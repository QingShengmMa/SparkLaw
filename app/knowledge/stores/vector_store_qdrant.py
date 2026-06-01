"""
Vector Store adapter — Qdrant 分布式向量数据库。

封装 Qdrant Client，提供统一的文档写入与检索能力。
针对法律场景优化，使用 COSINE 距离度量。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from app.core.logger import app_logger


EmbeddingFunction = Callable[[List[str]], List[List[float]]]


class VectorStoreAdapter:
    """基于 Qdrant 的向量库适配器（分布式架构）。"""

    def __init__(
        self,
        *,
        url: str,
        api_key: Optional[str] = None,
        collection_name: str,
        vector_size: int = 512,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Optional[Any] = None,
    ):
        """
        初始化 Qdrant 向量存储适配器。
        
        Args:
            url: Qdrant 服务地址（如 http://localhost:6333）
            api_key: Qdrant API Key（可选，用于云端部署）
            collection_name: Collection 名称
            vector_size: 向量维度（默认 512，对应 bge-small-zh-v1.5）
            metadata: Collection 元数据
            embedding_function: Embedding 模型实例
        """
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.metadata = metadata or {}
        self.embedding_function = embedding_function

        # 初始化 Qdrant 客户端
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=60,
        )
        
        # 创建或获取 Collection（使用 COSINE 距离，适合法律文本语义相似度）
        self._ensure_collection()
        
        app_logger.info(
            f"✅ Qdrant 向量库初始化完成: {self.collection_name} "
            f"(URL={self.url}, VectorSize={self.vector_size})"
        )

    def _ensure_collection(self):
        """确保 Collection 存在，不存在则创建。"""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,  # 法律场景使用余弦相似度
                    ),
                )
                app_logger.info(f"✅ 创建 Qdrant Collection: {self.collection_name}")
            else:
                app_logger.info(f"✅ Qdrant Collection 已存在: {self.collection_name}")
                
        except Exception as e:
            app_logger.error(f"❌ Qdrant Collection 初始化失败: {str(e)}")
            raise

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """使用 Embedding 模型生成向量。"""
        if not texts:
            return []
        if self.embedding_function is None:
            raise ValueError("embedding_function is required when embeddings are not provided")

        embedder = self.embedding_function
        if callable(embedder):
            vectors = embedder(texts)
        elif hasattr(embedder, "encode"):
            vectors = embedder.encode(
                texts, 
                show_progress_bar=False, 
                convert_to_numpy=True
            ).tolist()
        else:
            raise TypeError("Unsupported embedding_function type")

        return vectors

    def add_documents(
        self,
        *,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """
        批量添加文档到 Qdrant。
        
        Args:
            ids: 文档 ID 列表
            documents: 文档文本列表
            metadatas: 元数据列表
            embeddings: 向量列表（可选，不提供则自动生成）
        """
        if not ids or not documents:
            app_logger.warning("⚠️ 空文档列表，跳过添加")
            return
        
        if len(ids) != len(documents):
            raise ValueError("ids 和 documents 长度必须一致")
        
        # 生成向量（如果未提供）
        if embeddings is None:
            embeddings = self._embed_texts(documents)
        
        # 构造 Qdrant Points
        points = []
        for i, (doc_id, doc_text, embedding) in enumerate(zip(ids, documents, embeddings)):
            payload = {
                "text": doc_text,
                **(metadatas[i] if metadatas and i < len(metadatas) else {}),
            }
            points.append(
                PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload=payload,
                )
            )
        
        # 批量上传到 Qdrant
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            app_logger.info(f"✅ 成功添加 {len(points)} 个文档到 Qdrant")
        except Exception as e:
            app_logger.error(f"❌ Qdrant 添加文档失败: {str(e)}")
            raise

    def search(
        self,
        *,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        向量检索（支持元数据过滤）。
        
        Args:
            query_text: 查询文本（与 query_embedding 二选一）
            query_embedding: 查询向量
            n_results: 返回结果数量
            where: 元数据过滤条件（如 {"contract_id": "xxx"}）
            score_threshold: 相似度阈值（可选）
            
        Returns:
            检索结果，格式兼容 ChromaDB
        """
        if query_embedding is None and query_text is None:
            raise ValueError("query_text or query_embedding must be provided")

        # 生成查询向量
        if query_embedding is None and query_text is not None:
            query_embedding = self._embed_texts([query_text])[0]

        # 构造元数据过滤器
        query_filter = None
        if where:
            conditions = []
            for key, value in where.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )
            if conditions:
                query_filter = Filter(must=conditions)

        # 执行检索
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=n_results,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )
            
            # 转换为 ChromaDB 兼容格式
            ids = [str(hit.id) for hit in search_result]
            documents = [hit.payload.get("text", "") for hit in search_result]
            metadatas = [
                {k: v for k, v in hit.payload.items() if k != "text"}
                for hit in search_result
            ]
            # Qdrant 返回的是相似度分数（越高越好），转换为距离（越低越好）
            distances = [1.0 - hit.score for hit in search_result]
            
            return {
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
                "distances": [distances],
            }
            
        except Exception as e:
            app_logger.error(f"❌ Qdrant 检索失败: {str(e)}")
            raise

    def delete(self, *, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> int:
        """删除文档。"""
        try:
            if ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=ids,
                )
                app_logger.info(f"✅ 删除 {len(ids)} 个文档")
                return len(ids)
            
            elif where:
                conditions = []
                for key, value in where.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                query_filter = Filter(must=conditions)
                
                count_result = self.client.count(
                    collection_name=self.collection_name,
                    count_filter=query_filter,
                )
                count = count_result.count
                
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=query_filter,
                )
                app_logger.info(f"✅ 按条件删除 {count} 个文档")
                return count
            
            else:
                app_logger.warning("⚠️ 未提供删除条件，跳过删除")
                return 0
                
        except Exception as e:
            app_logger.error(f"❌ Qdrant 删除失败: {str(e)}")
            raise

    def get(self, *, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取文档（按 ID 或元数据过滤）。"""
        try:
            if ids:
                points = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=ids,
                )
                
                return {
                    "ids": [str(p.id) for p in points],
                    "documents": [p.payload.get("text", "") for p in points],
                    "metadatas": [
                        {k: v for k, v in p.payload.items() if k != "text"}
                        for p in points
                    ],
                }
            
            elif where:
                conditions = []
                for key, value in where.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                query_filter = Filter(must=conditions)
                
                points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=query_filter,
                    limit=10000,
                )
                
                return {
                    "ids": [str(p.id) for p in points],
                    "documents": [p.payload.get("text", "") for p in points],
                    "metadatas": [
                        {k: v for k, v in p.payload.items() if k != "text"}
                        for p in points
                    ],
                }
            
            else:
                points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=10000,
                )
                
                return {
                    "ids": [str(p.id) for p in points],
                    "documents": [p.payload.get("text", "") for p in points],
                    "metadatas": [
                        {k: v for k, v in p.payload.items() if k != "text"}
                        for p in points
                    ],
                }
                
        except Exception as e:
            app_logger.error(f"❌ Qdrant 获取文档失败: {str(e)}")
            raise

    def count(self) -> int:
        """获取 Collection 中的文档总数。"""
        try:
            result = self.client.count(collection_name=self.collection_name)
            return result.count
        except Exception as e:
            app_logger.error(f"❌ Qdrant 统计失败: {str(e)}")
            return 0

    # ---- 兼容 ChromaDB 接口的透传方法 ----

    def add(self, **kwargs):
        """兼容 ChromaDB 的 add 方法。"""
        return self.add_documents(**kwargs)

    def query(self, **kwargs):
        """兼容 ChromaDB 的 query 方法。"""
        if "query_embeddings" in kwargs:
            query_embeddings = kwargs.pop("query_embeddings")
            if query_embeddings and len(query_embeddings) > 0:
                kwargs["query_embedding"] = query_embeddings[0]
        
        if "n_results" in kwargs:
            kwargs["n_results"] = kwargs.pop("n_results")
        
        return self.search(**kwargs)
