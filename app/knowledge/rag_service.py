"""
RAG 向量检索服务
基于 ChromaDB 和 sentence-transformers 实现法律文档的语义检索
集成语义缓存机制，大幅降低高频相似查询的响应时间
"""

import os
import re
import uuid
import asyncio
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logger import app_logger
from app.services.legal_chunker import LegalChunker
from app.knowledge.retrievers.query_rewriter import QueryRewriter
from app.knowledge.retrievers.hybrid_retriever import HybridRetriever
from app.knowledge.rerankers.cross_encoder import Reranker
from app.knowledge.stores.vector_store_qdrant import VectorStoreAdapter
from app.knowledge.stores.legal_corpus_repo import LegalCorpusRepo
from app.knowledge.semantic_cache import get_semantic_cache


class RAGService:
    DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
    COLLECTION_NAME = "legal_contracts"
    LAW_COLLECTION_NAME = "legal_corpus"

    def __init__(self, embedding_model_name=None, qdrant_url=None):
        self.embedding_model_name = embedding_model_name or self.DEFAULT_EMBEDDING_MODEL
        self.qdrant_url = qdrant_url or settings.QDRANT_URL
        try:
            app_logger.info(f"🔄 正在加载 Embedding 模型: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            app_logger.info("✅ Embedding 模型加载完成")
            app_logger.info(f"🔄 正在初始化 Qdrant，服务地址: {self.qdrant_url}")

            self.contract_store = VectorStoreAdapter(
                url=self.qdrant_url,
                api_key=settings.QDRANT_API_KEY,
                collection_name=settings.QDRANT_COLLECTION_CONTRACTS,
                vector_size=settings.QDRANT_VECTOR_SIZE,
                metadata={"description": "法律合同文档向量库"},
                embedding_function=self.embedding_model,
            )
            self.collection = self.contract_store  # 兼容旧代码

            self.law_store = VectorStoreAdapter(
                url=self.qdrant_url,
                api_key=settings.QDRANT_API_KEY,
                collection_name=settings.QDRANT_COLLECTION_LAWS,
                vector_size=settings.QDRANT_VECTOR_SIZE,
                metadata={"description": "法律条文向量库"},
                embedding_function=self.embedding_model,
            )
            self.legal_corpus_repo = LegalCorpusRepo(self.law_store)

            app_logger.info(f"✅ Qdrant 初始化完成，集合: {settings.QDRANT_COLLECTION_CONTRACTS} / {settings.QDRANT_COLLECTION_LAWS}")
            self.chunker = LegalChunker()
            self.query_rewriter = QueryRewriter()
            self.reranker = Reranker()
            
            # ✅ 初始化混合检索器（Vector + BM25 + RRF）
            self.hybrid_retriever = HybridRetriever(k=60)
            app_logger.info("✅ 混合检索器已启用 (Vector + BM25 + RRF)")
            
            # ✅ 初始化语义缓存管理器
            self.semantic_cache = get_semantic_cache(embedding_model=self.embedding_model)
            if self.semantic_cache:
                app_logger.info("✅ 语义缓存已启用")
            else:
                app_logger.info("🔕 语义缓存未启用")
                
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
            self.contract_store.add_documents(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
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
        
        from app.core.profiler import rag_stage_timer
        _qp = query[:20]
        
        # ✅ 步骤1：检查语义缓存
        cache_result = None
        if self.semantic_cache:
            with rag_stage_timer("cache_check", _qp):
                cache_result = await self.semantic_cache.check_cache(query)
        
        # ✅ 步骤2：如果缓存命中，直接返回缓存的上下文
        if cache_result and cache_result.get("hit"):
            app_logger.info(f"🚀 缓存命中，跳过 Rewrite/Recall/Rerank，相似度: {cache_result.get('similarity', 0):.4f}")
            
            # 从缓存的 context 中解析出候选项
            # 注意：这里需要根据你的 context 格式进行解析
            # 假设 context 是 JSON 字符串或者直接是文本
            cached_context = cache_result.get("context", "")
            
            # 如果 context 是序列化的候选项列表，需要反序列化
            # 这里简化处理：直接返回一个包含缓存内容的候选项
            return [{
                "text": cached_context,
                "metadata": {
                    "source": "semantic_cache",
                    "cached_at": cache_result.get("cached_at", ""),
                    "similarity": cache_result.get("similarity", 0),
                    "original_query": cache_result.get("original_query", ""),
                },
                "similarity": cache_result.get("similarity", 0),
                "from_cache": True,
            }]
        
        # ✅ 步骤3：缓存未命中，执行标准 RAG 链路
        candidates: List[Dict[str, Any]] = []
        rewritten_query = query
        
        try:
            with rag_stage_timer("rewrite", _qp):
                rewritten_query = await self.query_rewriter.rewrite(query)

            with rag_stage_timer("recall", _qp):
                query_embedding = self.embedding_model.encode([rewritten_query], show_progress_bar=False, convert_to_numpy=True).tolist()[0]
                where_filter = {"contract_id": contract_id} if contract_id else None
                raw_results = self.contract_store.search(
                    query_embedding=query_embedding,
                    n_results=max(recall_top_k, top_k),
                    where=where_filter,
                )
            if raw_results and raw_results.get("documents") and raw_results["documents"][0]:
                docs = raw_results["documents"][0]
                metas = raw_results.get("metadatas", [[]])[0]
                dists = raw_results.get("distances", [[]])[0]
                for i, doc in enumerate(docs):
                    dist = dists[i] if i < len(dists) else None
                    sim = (1 - dist) if dist is not None else None
                    candidates.append({"text": doc, "metadata": metas[i] if i < len(metas) else {}, "distance": dist, "similarity": sim})

            # ✅ 新增：混合检索（Vector + BM25 + RRF 融合）
            with rag_stage_timer("hybrid_retrieve", _qp):
                if candidates:
                    # 使用混合检索器融合向量检索和 BM25 检索结果
                    candidates = self.hybrid_retriever.hybrid_retrieve(
                        query=rewritten_query,
                        vector_results=candidates,
                        top_k=recall_top_k,  # 先融合出更多候选，再由 reranker 精排
                        bm25_top_k=recall_top_k,
                    )

            with rag_stage_timer("rerank", _qp):
                reranked = self.reranker.rerank(query=rewritten_query, candidates=candidates, top_k=top_k)

            with rag_stage_timer("dedup", _qp):
                reranked = self._dedup_retrieved_candidates(reranked)

            final_results = reranked[:top_k]
            
            # ✅ 步骤4：异步保存到缓存（不阻塞主流程）
            if self.semantic_cache and final_results:
                # 将结果序列化为 context 字符串
                context_text = "\n\n---\n\n".join([
                    f"[片段 {i+1}]\n{item.get('text', '')}"
                    for i, item in enumerate(final_results)
                ])
                
                # 使用 asyncio.create_task 异步执行，不等待完成
                asyncio.create_task(
                    self.semantic_cache.save_to_cache(
                        query=query,
                        rewritten_query=rewritten_query,
                        context=context_text,
                        metadata={
                            "contract_id": contract_id,
                            "top_k": top_k,
                            "result_count": len(final_results),
                        }
                    )
                )
            
            return final_results
            
        except Exception as e:
            app_logger.error(f"\u274c Advanced \u68c0\u7d22\u5931\u8d25: {str(e)}")
            if candidates:
                return self._dedup_retrieved_candidates(sorted(candidates, key=lambda x: x.get("similarity") or -1, reverse=True))[:top_k]
            return []

    def delete_contract(self, contract_id: str):
        try:
            results = self.contract_store.get(where={"contract_id": contract_id})
            if results and results["ids"]:
                deleted_count = self.contract_store.delete(ids=results["ids"])
                return {"contract_id": contract_id, "deleted_count": deleted_count, "status": "success"}
            return {"contract_id": contract_id, "deleted_count": 0, "status": "not_found"}
        except Exception as e:
            return {"contract_id": contract_id, "deleted_count": 0, "status": "error", "error": str(e)}

    def get_contract_info(self, contract_id: str):
        results = self.contract_store.get(where={"contract_id": contract_id})
        if results and results["ids"]:
            return {"contract_id": contract_id, "chunk_count": len(results["ids"]), "exists": True}
        return {"contract_id": contract_id, "chunk_count": 0, "exists": False}

    def list_contracts(self):
        results = self.contract_store.get()
        if results and results.get("metadatas"):
            return sorted({m["contract_id"] for m in results["metadatas"] if "contract_id" in m})
        return []

    # ------------------------------------------------------------------
    # \u6cd5\u5f8b\u6761\u6587\u5e93\uff08\u72ec\u7acb collection\uff0c\u4e0e\u5408\u540c\u5e93\u5b8c\u5168\u9694\u79bb\uff09
    # ------------------------------------------------------------------

    def _get_law_collection(self):
        return self.law_store.collection

    def ingest_law(self, text: str, law_name: str, source: str = "", extra_metadata=None):
        law_id = law_name.strip() or str(uuid.uuid4())
        app_logger.info(f"📥 开始入库法律条文: {law_id}")
        chunks = self.chunker.chunk_text(text)
        if not chunks:
            return {"law_name": law_id, "chunk_count": 0, "status": "empty"}

        embeddings = self.embedding_model.encode(chunks, show_progress_bar=False, convert_to_numpy=True).tolist()
        safe_id = re.sub(r"[^\w\-]", "_", law_id)
        ids = [f"law_{safe_id}_{i}" for i in range(len(chunks))]

        metadatas = []
        for i, chunk in enumerate(chunks):
            m: Dict[str, Any] = {
                "law_name": law_id,
                "source": source or law_id,
                "chunk_index": i,
                "chunk_length": len(chunk),
                "doc_type": "law",
            }
            lm = self.chunker.get_chunk_metadata(chunk)
            if lm.get("chapter"):
                m["chapter"] = lm["chapter"]
            if lm.get("article"):
                m["article"] = lm["article"]
            if extra_metadata:
                m.update(extra_metadata)
            metadatas.append(m)

        try:
            self.legal_corpus_repo.delete_by_law_id(law_id)
        except Exception:
            pass

        self.legal_corpus_repo.add_law_chunks(
            ids=ids,
            chunks=chunks,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        app_logger.info(f"✅ 法律条文 {law_id} 入库完成，共 {len(chunks)} 个片段")
        return {"law_name": law_id, "chunk_count": len(chunks), "status": "success"}

    async def retrieve_law(self, query: str, top_k=5, recall_top_k=20, law_name=None):
        if not query or not query.strip():
            return []
        try:
            if self.legal_corpus_repo.count() == 0:
                return []
        except Exception:
            return []

        from app.core.profiler import rag_stage_timer
        _qp = query[:20]
        
        # ✅ 步骤1：检查语义缓存（法律条文专用缓存键）
        cache_key = f"law:{query}" if not law_name else f"law:{law_name}:{query}"
        cache_result = None
        if self.semantic_cache:
            with rag_stage_timer("cache_check", _qp):
                cache_result = await self.semantic_cache.check_cache(cache_key)
        
        # ✅ 步骤2：如果缓存命中，直接返回
        if cache_result and cache_result.get("hit"):
            app_logger.info(f"🚀 法律条文缓存命中，相似度: {cache_result.get('similarity', 0):.4f}")
            cached_context = cache_result.get("context", "")
            return [{
                "text": cached_context,
                "metadata": {
                    "source": "semantic_cache",
                    "cached_at": cache_result.get("cached_at", ""),
                    "similarity": cache_result.get("similarity", 0),
                },
                "similarity": cache_result.get("similarity", 0),
                "from_cache": True,
            }]
        
        # ✅ 步骤3：缓存未命中，执行标准检索
        candidates: List[Dict[str, Any]] = []
        rewritten_query = query
        
        try:
            with rag_stage_timer("rewrite", _qp):
                rewritten_query = await self.query_rewriter.rewrite(query)

            with rag_stage_timer("recall", _qp):
                emb = self.embedding_model.encode([rewritten_query], show_progress_bar=False, convert_to_numpy=True).tolist()[0]
                candidates = self.legal_corpus_repo.retrieve_by_query(
                    query_embedding=emb,
                    top_k=top_k,
                    recall_top_k=recall_top_k,
                    law_name=law_name,
                )

            # ✅ 新增：混合检索（Vector + BM25 + RRF 融合）
            with rag_stage_timer("hybrid_retrieve", _qp):
                if candidates:
                    candidates = self.hybrid_retriever.hybrid_retrieve(
                        query=rewritten_query,
                        vector_results=candidates,
                        top_k=recall_top_k,
                        bm25_top_k=recall_top_k,
                    )

            with rag_stage_timer("rerank", _qp):
                reranked = self.reranker.rerank(query=rewritten_query, candidates=candidates, top_k=top_k)

            with rag_stage_timer("dedup", _qp):
                reranked = self._dedup_retrieved_candidates(reranked)

            final_results = reranked[:top_k]
            
            # ✅ 步骤4：异步保存到缓存
            if self.semantic_cache and final_results:
                context_text = "\n\n---\n\n".join([
                    f"[法条 {i+1}]\n{item.get('text', '')}"
                    for i, item in enumerate(final_results)
                ])
                
                asyncio.create_task(
                    self.semantic_cache.save_to_cache(
                        query=cache_key,
                        rewritten_query=rewritten_query,
                        context=context_text,
                        metadata={
                            "law_name": law_name,
                            "top_k": top_k,
                            "result_count": len(final_results),
                            "query_type": "law",
                        }
                    )
                )
            
            return final_results
            
        except Exception as e:
            app_logger.error(f"❌ 法律条文检索失败: {str(e)}")
            return self._dedup_retrieved_candidates(sorted(candidates, key=lambda x: x.get("similarity") or -1, reverse=True))[:top_k] if candidates else []

    def list_laws(self):
        try:
            results = self.law_store.get()
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
        try:
            deleted = self.legal_corpus_repo.delete_by_law_id(law_name)
            if deleted > 0:
                return {"law_name": law_name, "deleted_count": deleted, "status": "success"}
            return {"law_name": law_name, "deleted_count": 0, "status": "not_found"}
        except Exception as e:
            return {"law_name": law_name, "deleted_count": 0, "status": "error", "error": str(e)}


_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance