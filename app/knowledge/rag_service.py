"""
RAG 向量检索服务
基于 ChromaDB 和 sentence-transformers 实现法律文档的语义检索
"""

import os
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
    """
    RAG (Retrieval-Augmented Generation) 向量检索服务。

    核心功能：
    1. 使用轻量级中文 Embedding 模型进行向量化
    2. 基于 ChromaDB 进行本地持久化存储
    3. 支持按 contract_id 进行隔离检索
    4. Advanced RAG：Query Rewrite -> 召回 -> Rerank -> 去重
    """

    DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
    COLLECTION_NAME = "legal_contracts"

    def __init__(
        self,
        embedding_model_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
    ):
        self.embedding_model_name = embedding_model_name or self.DEFAULT_EMBEDDING_MODEL
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR

        try:
            os.makedirs(self.persist_directory, exist_ok=True)

            app_logger.info(f"🔄 正在加载 Embedding 模型: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            app_logger.info("✅ Embedding 模型加载完成")

            app_logger.info(f"🔄 正在初始化 ChromaDB，持久化目录: {self.persist_directory}")
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "法律合同文档向量库"},
            )
            app_logger.info(f"✅ ChromaDB 初始化完成，集合: {self.COLLECTION_NAME}")

            self.chunker = LegalChunker()
            self.query_rewriter = QueryRewriter()
            self.reranker = Reranker()

        except Exception as e:
            app_logger.error(f"❌ RAG 服务初始化失败: {str(e)}")
            raise Exception(f"RAG 服务初始化失败: {str(e)}")

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def _dedup_retrieved_candidates(
        self,
        candidates: List[Dict[str, Any]],
        similarity_threshold: float = 0.96,
    ) -> List[Dict[str, Any]]:
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
            app_logger.info(f"🧹 证据链去重: {len(candidates)} -> {len(deduped)}")
        return deduped

    def _is_law_candidate(self, text: str, metadata: Dict[str, Any]) -> bool:
        if metadata.get("article") or metadata.get("chapter"):
            return True
        law_markers = ["第", "条", "款", "法", "条例", "司法解释", "本法", "应当", "不得"]
        return sum(1 for m in law_markers if m in text) >= 3

    def classify_retrieved_candidates(
        self, candidates: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        deduped = self._dedup_retrieved_candidates(candidates)
        laws, evidences = [], []
        for item in deduped:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            (laws if self._is_law_candidate(text, item.get("metadata") or {}) else evidences).append(item)
        return {"laws": laws, "evidences": evidences}

    # ------------------------------------------------------------------
    # 入库
    # ------------------------------------------------------------------

    def ingest_contract(
        self,
        text: str,
        contract_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not contract_id:
            contract_id = str(uuid.uuid4())
        app_logger.info(f"📥 开始入库合同: {contract_id}")
        try:
            chunks = self.chunker.chunk_text(text)
            if not chunks:
                app_logger.warning(f"⚠️  合同 {contract_id} 切片结果为空")
                return {"contract_id": contract_id, "chunk_count": 0, "status": "empty"}

            app_logger.info(f"📊 合同 {contract_id} 共切分为 {len(chunks)} 个片段")
            embeddings = self.embedding_model.encode(
                chunks, show_progress_bar=False, convert_to_numpy=True
            ).tolist()

            ids = [f"{contract_id}_{i}" for i in range(len(chunks))]
            metadatas = []
            for i, chunk in enumerate(chunks):
                m = {"contract_id": contract_id, "chunk_index": i, "chunk_length": len(chunk)}
                legal_meta = self.chunker.get_chunk_metadata(chunk)
                if legal_meta.get("chapter"):
                    m["chapter"] = legal_meta["chapter"]
                if legal_meta.get("article"):
                    m["article"] = legal_meta["article"]
                if metadata:
                    m.update(metadata)
                metadatas.append(m)

            self.collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
            app_logger.info(f"✅ 合同 {contract_id} 入库完成，共 {len(chunks)} 个片段")
            return {"contract_id": contract_id, "chunk_count": len(chunks), "status": "success"}
        except Exception as e:
            app_logger.error(f"❌ 合同 {contract_id} 入库失败: {str(e)}")
            raise Exception(f"合同入库失败: {str(e)}")

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------

    async def retrieve_clauses(
        self,
        query: str,
        contract_id: Optional[str] = None,
        top_k: int = 3,
        recall_top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        """Advanced RAG 检索链路：Query Rewrite -> 召回 -> Rerank -> 去重。"""
        if not query or not query.strip():
            return []

        candidates: List[Dict[str, Any]] = []
        try:
            rewritten_query = await self.query_rewriter.rewrite(query)
            app_logger.info(f"🧠 Query Rewrite: {query[:30]} -> {rewritten_query[:60]}")

            query_embedding = self.embedding_model.encode(
                [rewritten_query], show_progress_bar=False, convert_to_numpy=True
            ).tolist()[0]

            where_filter = {"contract_id": contract_id} if contract_id else None
            raw_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max(recall_top_k, top_k),
                where=where_filter,
            )

            if raw_results and raw_results.get("documents") and raw_results["documents"][0]:
                documents = raw_results["documents"][0]
                metadatas = raw_results.get("metadatas", [[]])[0]
                distances = raw_results.get("distances", [[]])[0]
                for i, doc in enumerate(documents):
                    distance = distances[i] if i < len(distances) else None
                    similarity = (1 - distance) if distance is not None else None
                    candidates.append({"text": doc, "metadata": metadatas[i] if i < len(metadatas) else {}, "distance": distance, "similarity": similarity})

            reranked = self.reranker.rerank(query=rewritten_query, candidates=candidates, top_k=top_k)
            reranked = self._dedup_retrieved_candidates(reranked)
            app_logger.info(f"✅ Advanced 检索完成，候选 {len(candidates)} -> 返回 {len(reranked)}")
            return reranked[:top_k]

        except Exception as e:
            app_logger.error(f"❌ Advanced 检索失败: {str(e)}")
            if candidates:
                deduped = self._dedup_retrieved_candidates(
                    sorted(candidates, key=lambda x: x.get("similarity") or -1, reverse=True)
                )
                return deduped[:top_k]
            return []

    # ------------------------------------------------------------------
    # 管理
    # ------------------------------------------------------------------

    def delete_contract(self, contract_id: str) -> Dict[str, Any]:
        app_logger.info(f"🗑️  删除合同: {contract_id}")
        try:
            results = self.collection.get(where={"contract_id": contract_id})
            if results and results["ids"]:
                self.collection.delete(ids=results["ids"])
                deleted_count = len(results["ids"])
                app_logger.info(f"✅ 合同 {contract_id} 删除完成，共删除 {deleted_count} 个片段")
                return {"contract_id": contract_id, "deleted_count": deleted_count, "status": "success"}
            return {"contract_id": contract_id, "deleted_count": 0, "status": "not_found"}
        except Exception as e:
            return {"contract_id": contract_id, "deleted_count": 0, "status": "error", "error": str(e)}

    def get_contract_info(self, contract_id: str) -> Dict[str, Any]:
        results = self.collection.get(where={"contract_id": contract_id})
        if results and results["ids"]:
            return {"contract_id": contract_id, "chunk_count": len(results["ids"]), "exists": True}
        return {"contract_id": contract_id, "chunk_count": 0, "exists": False}

    def list_contracts(self) -> List[str]:
        results = self.collection.get()
        if results and results.get("metadatas"):
            return sorted({m["contract_id"] for m in results["metadatas"] if "contract_id" in m})
        return []


_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
