"""
语义缓存管理器
基于 ChromaDB 实现高频相似查询的缓存机制，大幅降低 RAG 链路耗时
"""

import time
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.logger import app_logger


class SemanticCacheManager:
    """
    语义缓存管理器
    
    核心功能：
    1. 使用 ChromaDB 存储 (原始Query, 改写Query, 召回Context) 三元组
    2. 通过向量相似度检索判断缓存命中
    3. 异步写入缓存，不阻塞主流程
    """
    
    CACHE_COLLECTION_NAME = "semantic_cache"
    
    def __init__(self, embedding_model, persist_directory: str = None):
        """
        初始化语义缓存管理器
        
        Args:
            embedding_model: 复用的 SentenceTransformer 模型实例
            persist_directory: ChromaDB 持久化目录
        """
        self.embedding_model = embedding_model
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR
        self.enabled = settings.ENABLE_SEMANTIC_CACHE
        self.threshold = settings.SEMANTIC_CACHE_THRESHOLD
        self.top_k = settings.SEMANTIC_CACHE_TOP_K
        self.ttl_days = settings.SEMANTIC_CACHE_TTL_DAYS
        
        if not self.enabled:
            app_logger.info("🔕 语义缓存已禁用")
            self.cache_store = None
            return
        
        try:
            from app.knowledge.stores.vector_store_qdrant import VectorStoreAdapter

            app_logger.info(f"🔄 正在初始化语义缓存，阈值: {self.threshold}")
            self.cache_store = VectorStoreAdapter(
                persist_directory=self.persist_directory,
                collection_name=self.CACHE_COLLECTION_NAME,
                metadata={"description": "RAG 语义缓存"},
                embedding_function=self.embedding_model,
            )
            app_logger.info(f"✅ 语义缓存初始化完成，当前缓存条目: {self.cache_store.count()}")
        except Exception as e:
            app_logger.error(f"❌ 语义缓存初始化失败: {str(e)}")
            self.enabled = False
            self.cache_store = None
    
    async def check_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """
        检查缓存是否命中
        
        Args:
            query: 用户原始查询
            
        Returns:
            如果命中，返回 {
                "hit": True,
                "rewritten_query": str,
                "context": str,
                "similarity": float,
                "cached_at": str
            }
            如果未命中，返回 None
        """
        if not self.enabled or not self.cache_store:
            return None
        
        if not query or not query.strip():
            return None
        
        try:
            start_time = time.time()
            
            # 使用现有的 embedding 模型进行向量化（复用，不重新加载）
            query_embedding = self.embedding_model.encode(
                [query.strip()],
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()[0]
            
            # 在缓存 collection 中检索最相似的条目
            results = self.cache_store.search(
                query_embedding=query_embedding,
                n_results=self.top_k,
            )
            
            if not results or not results.get("documents") or not results["documents"][0]:
                elapsed = (time.time() - start_time) * 1000
                app_logger.debug(f"🔍 缓存未命中 [{elapsed:.1f}ms]: {query[:30]}...")
                return None
            
            # 获取最相似的结果
            top_doc = results["documents"][0][0]
            top_meta = results["metadatas"][0][0] if results.get("metadatas") else {}
            top_distance = results["distances"][0][0] if results.get("distances") else 1.0
            
            # 计算相似度（ChromaDB 默认使用 L2 距离，需要转换为余弦相似度）
            # 对于归一化向量，L2距离和余弦相似度的关系: similarity = 1 - (distance^2 / 2)
            # 简化处理：similarity ≈ 1 - distance
            similarity = 1.0 - top_distance
            
            elapsed = (time.time() - start_time) * 1000
            
            # 判断是否超过阈值
            if similarity >= self.threshold:
                app_logger.info(
                    f"✅ 缓存命中 [{elapsed:.1f}ms] 相似度: {similarity:.4f} | "
                    f"原始: {query[:30]}... | 缓存: {top_doc[:30]}..."
                )
                
                return {
                    "hit": True,
                    "rewritten_query": top_meta.get("rewritten_query", ""),
                    "context": top_meta.get("context", ""),
                    "similarity": similarity,
                    "cached_at": top_meta.get("cached_at", ""),
                    "original_query": top_doc,
                }
            else:
                app_logger.debug(
                    f"🔍 缓存未命中 [{elapsed:.1f}ms] 相似度: {similarity:.4f} < {self.threshold} | "
                    f"{query[:30]}..."
                )
                return None
                
        except Exception as e:
            app_logger.error(f"❌ 缓存检查失败: {str(e)}")
            return None
    
    async def save_to_cache(
        self,
        query: str,
        rewritten_query: str,
        context: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        异步保存到缓存（后台任务，不阻塞主流程）
        
        Args:
            query: 用户原始查询
            rewritten_query: 改写后的查询
            context: 召回并重排后的上下文
            metadata: 额外的元数据
            
        Returns:
            是否保存成功
        """
        if not self.enabled or not self.cache_store:
            return False
        
        if not query or not query.strip():
            return False
        
        try:
            # 生成唯一 ID（使用时间戳 + 查询哈希）
            import hashlib
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            cache_id = f"cache_{int(time.time())}_{query_hash}"
            
            # 构建元数据
            cache_metadata = {
                "rewritten_query": rewritten_query or "",
                "context": context or "",
                "cached_at": datetime.now().isoformat(),
                "query_length": len(query),
                "context_length": len(context) if context else 0,
            }
            
            if metadata:
                cache_metadata.update(metadata)
            
            # 向量化原始查询
            query_embedding = self.embedding_model.encode(
                [query.strip()],
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()[0]
            
            # 写入缓存
            self.cache_store.add_documents(
                ids=[cache_id],
                documents=[query.strip()],
                embeddings=[query_embedding],
                metadatas=[cache_metadata],
            )
            
            app_logger.info(f"💾 缓存已保存: {query[:30]}... -> {cache_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"❌ 缓存保存失败: {str(e)}")
            return False
    
    def clear_expired_cache(self, days: int = None) -> int:
        """
        清理过期缓存
        
        Args:
            days: 保留最近 N 天的缓存，默认使用配置的 TTL
            
        Returns:
            清理的条目数
        """
        if not self.enabled or not self.cache_store:
            return 0
        
        try:
            days = days or self.ttl_days
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()
            
            # 获取所有缓存条目
            all_results = self.cache_store.get()
            
            if not all_results or not all_results.get("ids"):
                return 0
            
            # 筛选过期条目
            expired_ids = []
            for i, meta in enumerate(all_results.get("metadatas", [])):
                cached_at = meta.get("cached_at", "")
                if cached_at and cached_at < cutoff_iso:
                    expired_ids.append(all_results["ids"][i])
            
            # 删除过期条目
            if expired_ids:
                self.cache_store.delete(ids=expired_ids)
                app_logger.info(f"🧹 已清理 {len(expired_ids)} 条过期缓存（>{days}天）")
                return len(expired_ids)
            
            return 0
            
        except Exception as e:
            app_logger.error(f"❌ 清理过期缓存失败: {str(e)}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计数据
        """
        if not self.enabled or not self.cache_store:
            return {
                "enabled": False,
                "total_entries": 0,
                "threshold": self.threshold,
            }
        
        try:
            total = self.cache_store.count()
            return {
                "enabled": True,
                "total_entries": total,
                "threshold": self.threshold,
                "ttl_days": self.ttl_days,
                "collection_name": self.CACHE_COLLECTION_NAME,
            }
        except Exception as e:
            app_logger.error(f"❌ 获取缓存统计失败: {str(e)}")
            return {
                "enabled": True,
                "total_entries": 0,
                "threshold": self.threshold,
                "error": str(e),
            }
    
    def clear_all_cache(self) -> bool:
        """
        清空所有缓存（危险操作，仅用于测试或维护）
        
        Returns:
            是否清空成功
        """
        if not self.enabled or not self.cache_store:
            return False
        
        try:
            all_results = self.cache_store.get()
            if all_results and all_results.get("ids"):
                self.cache_store.delete(ids=all_results["ids"])
                app_logger.warning(f"⚠️ 已清空所有缓存，共 {len(all_results['ids'])} 条")
                return True
            return True
        except Exception as e:
            app_logger.error(f"❌ 清空缓存失败: {str(e)}")
            return False


# 全局单例
_semantic_cache_instance: Optional[SemanticCacheManager] = None


def get_semantic_cache(embedding_model=None) -> Optional[SemanticCacheManager]:
    """
    获取语义缓存管理器单例
    
    Args:
        embedding_model: Embedding 模型实例（首次调用时必须提供）
        
    Returns:
        SemanticCacheManager 实例或 None（如果缓存被禁用）
    """
    global _semantic_cache_instance
    
    if not settings.ENABLE_SEMANTIC_CACHE:
        return None
    
    if _semantic_cache_instance is None:
        if embedding_model is None:
            raise ValueError("首次调用 get_semantic_cache 时必须提供 embedding_model")
        _semantic_cache_instance = SemanticCacheManager(embedding_model)
    
    return _semantic_cache_instance
