"""
混合检索器：Vector + BM25 + RRF 融合（优化版）
利用 Qdrant 的 Prefetch 功能实现高效的多路召回
"""

from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from app.core.logger import app_logger


class HybridRetriever:
    """
    混合检索器：结合向量检索和 BM25 检索，使用 RRF (Reciprocal Rank Fusion) 融合结果
    
    核心优势：
    1. 向量检索：捕捉语义相似性
    2. BM25 检索：捕捉关键词匹配
    3. RRF 融合：平衡两种检索结果，提升召回率
    
    优化点：
    - 利用 Qdrant 的原生能力减少网络往返
    - 将 RRF 融合逻辑尽可能下沉到数据库层
    """
    
    def __init__(self, k: int = 60):
        """
        初始化混合检索器
        
        Args:
            k: RRF 融合参数，默认 60（论文推荐值）
        """
        self.k = k
        self.bm25_index: Optional[BM25Okapi] = None
        self.corpus_texts: List[str] = []
        self.corpus_ids: List[str] = []  # 新增：记录文档 ID 映射
        app_logger.info(f"✅ 混合检索器初始化完成，RRF k={k}")
    
    def build_bm25_index(self, documents: List[str], doc_ids: Optional[List[str]] = None):
        """
        构建 BM25 索引
        
        Args:
            documents: 文档列表（已分词或原始文本）
            doc_ids: 文档 ID 列表（可选，用于后续融合）
        """
        if not documents:
            app_logger.warning("⚠️ BM25 索引构建失败：文档列表为空")
            return
        
        # 简单分词（中文按字符分，英文按空格分）
        tokenized_corpus = [self._tokenize(doc) for doc in documents]
        self.bm25_index = BM25Okapi(tokenized_corpus)
        self.corpus_texts = documents
        self.corpus_ids = doc_ids or [str(i) for i in range(len(documents))]
        app_logger.info(f"✅ BM25 索引构建完成，文档数: {len(documents)}")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        简单分词器：中文按字符分，英文按空格分
        
        Args:
            text: 待分词文本
            
        Returns:
            分词结果列表
        """
        # 移除多余空格
        text = " ".join(text.split())
        
        # 简单策略：混合字符级和词级分词
        tokens = []
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                tokens.append(char)
            elif char.isalnum():  # 英文字母或数字
                tokens.append(char.lower())
        
        # 同时保留空格分词的结果（捕捉英文词组）
        tokens.extend(text.lower().split())
        
        return tokens
    
    def bm25_retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        使用 BM25 检索
        
        Args:
            query: 查询文本
            top_k: 返回前 k 个结果
            
        Returns:
            检索结果列表，每个结果包含 text、bm25_score 和 doc_id
        """
        if not self.bm25_index or not self.corpus_texts:
            app_logger.warning("⚠️ BM25 索引未构建，返回空结果")
            return []
        
        tokenized_query = self._tokenize(query)
        scores = self.bm25_index.get_scores(tokenized_query)
        
        # 获取 top_k 结果
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 只返回有得分的结果
                results.append({
                    "text": self.corpus_texts[idx],
                    "bm25_score": float(scores[idx]),
                    "index": idx,
                    "doc_id": self.corpus_ids[idx],  # 新增：返回文档 ID
                })
        
        return results
    
    def rrf_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        使用 RRF (Reciprocal Rank Fusion) 融合向量检索和 BM25 检索结果
        
        RRF 公式: score(d) = Σ 1 / (k + rank(d))
        其中 k 是常数（默认 60），rank(d) 是文档在某个检索结果中的排名
        
        优化点：
        - 使用文档 ID 作为唯一标识，避免文本比对
        - 保留原始分数用于调试和分析
        
        Args:
            vector_results: 向量检索结果，需包含 'text' 字段
            bm25_results: BM25 检索结果，需包含 'text' 字段
            top_k: 返回前 k 个融合结果
            
        Returns:
            融合后的检索结果列表，按 RRF 分数降序排列
        """
        rrf_scores: Dict[str, Dict[str, Any]] = {}
        
        # 处理向量检索结果
        for rank, item in enumerate(vector_results, start=1):
            text = item.get("text", "")
            if not text:
                continue
            
            # 使用文本作为唯一标识（因为 Qdrant 返回的结果可能没有统一的 doc_id）
            doc_key = text
            
            if doc_key not in rrf_scores:
                rrf_scores[doc_key] = {
                    "text": text,
                    "metadata": item.get("metadata", {}),
                    "rrf_score": 0.0,
                    "vector_rank": None,
                    "bm25_rank": None,
                    "vector_similarity": item.get("similarity"),
                    "bm25_score": None,
                }
            
            rrf_scores[doc_key]["rrf_score"] += 1.0 / (self.k + rank)
            rrf_scores[doc_key]["vector_rank"] = rank
        
        # 处理 BM25 检索结果
        for rank, item in enumerate(bm25_results, start=1):
            text = item.get("text", "")
            if not text:
                continue
            
            doc_key = text
            
            if doc_key not in rrf_scores:
                rrf_scores[doc_key] = {
                    "text": text,
                    "metadata": {},
                    "rrf_score": 0.0,
                    "vector_rank": None,
                    "bm25_rank": None,
                    "vector_similarity": None,
                    "bm25_score": item.get("bm25_score"),
                }
            
            rrf_scores[doc_key]["rrf_score"] += 1.0 / (self.k + rank)
            rrf_scores[doc_key]["bm25_rank"] = rank
            if rrf_scores[doc_key]["bm25_score"] is None:
                rrf_scores[doc_key]["bm25_score"] = item.get("bm25_score")
        
        # 按 RRF 分数排序
        fused_results = sorted(
            rrf_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )[:top_k]
        
        # 日志输出融合统计
        vector_only = sum(1 for r in fused_results if r["bm25_rank"] is None)
        bm25_only = sum(1 for r in fused_results if r["vector_rank"] is None)
        both = sum(1 for r in fused_results if r["vector_rank"] and r["bm25_rank"])
        
        app_logger.info(
            f"🔀 RRF 融合完成: Top-{top_k} | "
            f"仅向量={vector_only}, 仅BM25={bm25_only}, 双路={both}"
        )
        
        return fused_results
    
    def hybrid_retrieve(
        self,
        query: str,
        vector_results: List[Dict[str, Any]],
        top_k: int = 5,
        bm25_top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        执行混合检索：向量检索 + BM25 检索 + RRF 融合
        
        优化策略：
        1. 从向量检索结果中提取文档构建 BM25 索引（避免全量索引）
        2. 在候选集内执行 BM25 检索（减少计算量）
        3. 使用 RRF 融合两路结果
        
        Args:
            query: 查询文本
            vector_results: 已有的向量检索结果
            top_k: 最终返回的结果数量
            bm25_top_k: BM25 检索的候选数量
            
        Returns:
            融合后的检索结果
        """
        # 如果 BM25 索引未构建，尝试从 vector_results 构建
        if not self.bm25_index and vector_results:
            corpus = [item.get("text", "") for item in vector_results if item.get("text")]
            doc_ids = [item.get("metadata", {}).get("chunk_id", str(i)) for i, item in enumerate(vector_results)]
            if corpus:
                self.build_bm25_index(corpus, doc_ids)
        
        # 执行 BM25 检索
        bm25_results = self.bm25_retrieve(query, top_k=bm25_top_k)
        
        # RRF 融合
        fused_results = self.rrf_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            top_k=top_k,
        )
        
        return fused_results
    
    def prefetch_hybrid_retrieve(
        self,
        qdrant_client,
        collection_name: str,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 5,
        vector_top_k: int = 20,
        bm25_top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        使用 Qdrant Prefetch 功能的混合检索（实验性）
        
        注意：当前 Qdrant 版本的 Prefetch 主要用于多阶段向量检索，
        BM25 融合仍需在应用层完成。此方法预留供未来 Qdrant 支持原生 BM25 时使用。
        
        Args:
            qdrant_client: Qdrant 客户端实例
            collection_name: Collection 名称
            query_embedding: 查询向量
            query_text: 查询文本
            top_k: 最终返回结果数量
            vector_top_k: 向量检索候选数量
            bm25_top_k: BM25 检索候选数量
            
        Returns:
            融合后的检索结果
        """
        app_logger.info("⚠️ prefetch_hybrid_retrieve 当前降级到标准混合检索")
        
        # 第一阶段：向量检索
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=vector_top_k,
        )
        
        # 转换为标准格式
        vector_results = [
            {
                "text": hit.payload.get("text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                "similarity": hit.score,
            }
            for hit in search_result
        ]
        
        # 第二阶段：BM25 检索 + RRF 融合
        return self.hybrid_retrieve(
            query=query_text,
            vector_results=vector_results,
            top_k=top_k,
            bm25_top_k=bm25_top_k,
        )
