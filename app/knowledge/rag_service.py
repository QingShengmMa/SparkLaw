"""
RAG 向量检索服务
基于 ChromaDB 和 sentence-transformers 实现法律文档的语义检索
"""

import os
import re
import uuid
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logger import app_logger
from app.services.legal_chunker import LegalChunker
from app.knowledge.retrievers.query_rewriter import QueryRewriter
from app.knowledge.rerankers.cross_encoder import Reranker


class RAGService:
    DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
    COLLECTION_NAME = "legal_contracts"
    LAW_COLLECTION_NAME = "legal_corpus"

    def __init__(self, embedding_model_name=None, persist_directory=None):
        self.embedding_model_name = embedding_model_name or self.DEFAULT_EMBEDDING_MODEL
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            app_logger.info(f"\U0001f504 \u6b63\u5728\u52a0\u8f7d Embedding \u6a21\u578b: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            app_logger.info("\u2705 Embedding \u6a21\u578b\u52a0\u8f7d\u5b8c\u6210")
            app_logger.info(f"\U0001f504 \u6b63\u5728\u521d\u59cb\u5316 ChromaDB\uff0c\u6301\u4e45\u5316\u76ee\u5f55: {self.persist_directory}")
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "\u6cd5\u5f8b\u5408\u540c\u6587\u6863\u5411\u91cf\u5e93"},
            )
            app_logger.info(f"\u2705 ChromaDB \u521d\u59cb\u5316\u5b8c\u6210\uff0c\u96c6\u5408: {self.COLLECTION_NAME}")
            self._law_collection = None
            self.chunker = LegalChunker()
            self.query_rewriter = QueryRewriter()
            self.reranker = Reranker()
        except Exception as e:
            app_logger.error(f"\u274c RAG \u670d\u52a1\u521d\u59cb\u5316\u5931\u8d25: {str(e)}")
            raise Exception(f"RAG \u670d\u52a1\u521d\u59cb\u5316\u5931\u8d25: {str(e)}")

    def _dedup_retrieved_candidates(self, candidates, similarity_threshold=0.96):
        deduped: List[Dict[str, Any]] = []
        seen_texts: List[str] = []
        for item in candidates:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            duplicated = any(
                text == ex or SequenceMatcher(None, text, ex).ratio() >= similarity_threshold
                for ex in seen_texts
            )
            if not duplicated:
                deduped.append(item)
                seen_texts.append(text)
        if len(deduped) < len(candidates):
            app_logger.info(f"\U0001f9f9 \u8bc1\u636e\u94fe\u53bb\u91cd: {len(candidates)} -> {len(deduped)}")
        return deduped

    def _is_law_candidate(self, text: str, metadata: Dict[str, Any]) -> bool:
        if metadata.get("article") or metadata.get("chapter"):
            return True
        law_markers = ["\u7b2c", "\u6761", "\u6b3e", "\u6cd5", "\u6761\u4f8b", "\u53f8\u6cd5\u89e3\u91ca", "\u672c\u6cd5", "\u5e94\u5f53", "\u4e0d\u5f97"]
        return sum(1 for m in law_markers if m in text) >= 3

    def classify_retrieved_candidates(self, candidates):
        deduped = self._dedup_retrieved_candidates(candidates)
        laws, evidences = [], []
        for item in deduped:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            (laws if self._is_law_candidate(text, item.get("metadata") or {}) else evidences).append(item)
        return {"laws": laws, "evidences": evidences}

    def ingest_contract(self, text: str, contract_id=None, metadata=None):
        if not contract_id:
            contract_id = str(uuid.uuid4())
        app_logger.info(f"\U0001f4e5 \u5f00\u59cb\u5165\u5e93\u5408\u540c: {contract_id}")
        try:
            chunks = self.chunker.chunk_text(text)
            if not chunks:
                return {"contract_id": contract_id, "chunk_count": 0, "status": "empty"}
            embeddings = self.embedding_model.encode(chunks, show_progress_bar=False, convert_to_numpy=True).tolist()
            ids = [f"{contract_id}_{i}" for i in range(len(chunks))]
            metadatas = []
            for i, chunk in enumerate(chunks):
                m = {"contract_id": contract_id, "chunk_index": i, "chunk_length": len(chunk)}
                lm = self.chunker.get_chunk_metadata(chunk)
                if lm.get("chapter"): m["chapter"] = lm["chapter"]
                if lm.get("article"): m["article"] = lm["article"]
                if metadata: m.update(metadata)
                metadatas.append(m)
            self.collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
            app_logger.info(f"\u2705 \u5408\u540c {contract_id} \u5165\u5e93\u5b8c\u6210\uff0c\u5171 {len(chunks)} \u4e2a\u7247\u6bb5")
            return {"contract_id": contract_id, "chunk_count": len(chunks), "status": "success"}
        except Exception as e:
            app_logger.error(f"\u274c \u5408\u540c {contract_id} \u5165\u5e93\u5931\u8d25: {str(e)}")
            raise Exception(f"\u5408\u540c\u5165\u5e93\u5931\u8d25: {str(e)}")

    async def add_document(self, text: str, contract_id=None, metadata=None):
        result = self.ingest_contract(text=text, contract_id=contract_id, metadata=metadata)
        return result.get("chunk_count", 0)

    async def retrieve_clauses(self, query: str, contract_id=None, top_k=3, recall_top_k=15):
        if not query or not query.strip():
            return []
        candidates: List[Dict[str, Any]] = []
        try:
            rewritten_query = await self.query_rewriter.rewrite(query)
            query_embedding = self.embedding_model.encode([rewritten_query], show_progress_bar=False, convert_to_numpy=True).tolist()[0]
            where_filter = {"contract_id": contract_id} if contract_id else None
            raw_results = self.collection.query(query_embeddings=[query_embedding], n_results=max(recall_top_k, top_k), where=where_filter)
            if raw_results and raw_results.get("documents") and raw_results["documents"][0]:
                docs = raw_results["documents"][0]
                metas = raw_results.get("metadatas", [[]])[0]
                dists = raw_results.get("distances", [[]])[0]
                for i, doc in enumerate(docs):
                    dist = dists[i] if i < len(dists) else None
                    sim = (1 - dist) if dist is not None else None
                    candidates.append({"text": doc, "metadata": metas[i] if i < len(metas) else {}, "distance": dist, "similarity": sim})
            reranked = self.reranker.rerank(query=rewritten_query, candidates=candidates, top_k=top_k)
            reranked = self._dedup_retrieved_candidates(reranked)
            return reranked[:top_k]
        except Exception as e:
            app_logger.error(f"\u274c Advanced \u68c0\u7d22\u5931\u8d25: {str(e)}")
            if candidates:
                return self._dedup_retrieved_candidates(sorted(candidates, key=lambda x: x.get("similarity") or -1, reverse=True))[:top_k]
            return []

    def delete_contract(self, contract_id: str):
        try:
            results = self.collection.get(where={"contract_id": contract_id})
            if results and results["ids"]:
                self.collection.delete(ids=results["ids"])
                return {"contract_id": contract_id, "deleted_count": len(results["ids"]), "status": "success"}
            return {"contract_id": contract_id, "deleted_count": 0, "status": "not_found"}
        except Exception as e:
            return {"contract_id": contract_id, "deleted_count": 0, "status": "error", "error": str(e)}

    def get_contract_info(self, contract_id: str):
        results = self.collection.get(where={"contract_id": contract_id})
        if results and results["ids"]:
            return {"contract_id": contract_id, "chunk_count": len(results["ids"]), "exists": True}
        return {"contract_id": contract_id, "chunk_count": 0, "exists": False}

    def list_contracts(self):
        results = self.collection.get()
        if results and results.get("metadatas"):
            return sorted({m["contract_id"] for m in results["metadatas"] if "contract_id" in m})
        return []

    # ------------------------------------------------------------------
    # \u6cd5\u5f8b\u6761\u6587\u5e93\uff08\u72ec\u7acb collection\uff0c\u4e0e\u5408\u540c\u5e93\u5b8c\u5168\u9694\u79bb\uff09
    # ------------------------------------------------------------------

    def _get_law_collection(self):
        if self._law_collection is None:
            self._law_collection = self.chroma_client.get_or_create_collection(
                name=self.LAW_COLLECTION_NAME,
                metadata={"description": "\u6cd5\u5f8b\u6761\u6587\u5411\u91cf\u5e93"},
            )
        return self._law_collection

    def ingest_law(self, text: str, law_name: str, source: str = "", extra_metadata=None):
        collection = self._get_law_collection()
        law_id = law_name.strip() or str(uuid.uuid4())
        app_logger.info(f"\U0001f4e5 \u5f00\u59cb\u5165\u5e93\u6cd5\u5f8b\u6761\u6587: {law_id}")
        chunks = self.chunker.chunk_text(text)
        if not chunks:
            return {"law_name": law_id, "chunk_count": 0, "status": "empty"}
        embeddings = self.embedding_model.encode(chunks, show_progress_bar=False, convert_to_numpy=True).tolist()
        safe_id = re.sub(r"[^\w\-]", "_", law_id)
        ids = [f"law_{safe_id}_{i}" for i in range(len(chunks))]
        metadatas = []
        for i, chunk in enumerate(chunks):
            m: Dict[str, Any] = {"law_name": law_id, "source": source or law_id, "chunk_index": i, "chunk_length": len(chunk), "doc_type": "law"}
            lm = self.chunker.get_chunk_metadata(chunk)
            if lm.get("chapter"): m["chapter"] = lm["chapter"]
            if lm.get("article"): m["article"] = lm["article"]
            if extra_metadata: m.update(extra_metadata)
            metadatas.append(m)
        try:
            old = collection.get(where={"law_name": law_id})
            if old and old["ids"]: collection.delete(ids=old["ids"])
        except Exception:
            pass
        collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        app_logger.info(f"\u2705 \u6cd5\u5f8b\u6761\u6587 {law_id} \u5165\u5e93\u5b8c\u6210\uff0c\u5171 {len(chunks)} \u4e2a\u7247\u6bb5")
        return {"law_name": law_id, "chunk_count": len(chunks), "status": "success"}

    async def retrieve_law(self, query: str, top_k=5, recall_top_k=20, law_name=None):
        if not query or not query.strip():
            return []
        collection = self._get_law_collection()
        try:
            if collection.count() == 0:
                return []
        except Exception:
            return []
        candidates: List[Dict[str, Any]] = []
        try:
            rewritten = await self.query_rewriter.rewrite(query)
            emb = self.embedding_model.encode([rewritten], show_progress_bar=False, convert_to_numpy=True).tolist()[0]
            where = {"law_name": law_name} if law_name else None
            raw = collection.query(query_embeddings=[emb], n_results=max(recall_top_k, top_k), where=where)
            if raw and raw.get("documents") and raw["documents"][0]:
                docs = raw["documents"][0]
                metas = raw.get("metadatas", [[]])[0]
                dists = raw.get("distances", [[]])[0]
                for i, doc in enumerate(docs):
                    dist = dists[i] if i < len(dists) else None
                    sim = (1 - dist) if dist is not None else None
                    candidates.append({"text": doc, "metadata": metas[i] if i < len(metas) else {}, "distance": dist, "similarity": sim})
            reranked = self.reranker.rerank(query=rewritten, candidates=candidates, top_k=top_k)
            reranked = self._dedup_retrieved_candidates(reranked)
            return reranked[:top_k]
        except Exception as e:
            app_logger.error(f"\u274c \u6cd5\u5f8b\u6761\u6587\u68c0\u7d22\u5931\u8d25: {str(e)}")
            return self._dedup_retrieved_candidates(sorted(candidates, key=lambda x: x.get("similarity") or -1, reverse=True))[:top_k] if candidates else []

    def list_laws(self):
        collection = self._get_law_collection()
        try:
            results = collection.get()
            if not results or not results.get("metadatas"):
                return []
            stats: Dict[str, int] = {}
            for m in results["metadatas"]:
                n = m.get("law_name", "unknown")
                stats[n] = stats.get(n, 0) + 1
            return [{"law_name": k, "chunk_count": v} for k, v in sorted(stats.items())]
        except Exception:
            return []

    def delete_law(self, law_name: str):
        collection = self._get_law_collection()
        try:
            results = collection.get(where={"law_name": law_name})
            if results and results["ids"]:
                collection.delete(ids=results["ids"])
                return {"law_name": law_name, "deleted_count": len(results["ids"]), "status": "success"}
            return {"law_name": law_name, "deleted_count": 0, "status": "not_found"}
        except Exception as e:
            return {"law_name": law_name, "deleted_count": 0, "status": "error", "error": str(e)}


_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance