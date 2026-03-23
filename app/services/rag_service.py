"""
RAG 向量检索服务
基于 ChromaDB 和 sentence-transformers 实现法律文档的语义检索
"""

import os
import uuid
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from app.core.logger import app_logger
from app.services.legal_chunker import LegalChunker
from app.services.retrieval.query_rewriter import QueryRewriter
from app.services.retrieval.reranker import Reranker


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) 向量检索服务
    
    核心功能：
    1. 使用轻量级中文 Embedding 模型进行向量化
    2. 基于 ChromaDB 进行本地持久化存储
    3. 支持按 contract_id 进行隔离检索
    4. 提供高效的语义相似度搜索
    
    技术栈：
    - Embedding 模型：BAAI/bge-small-zh-v1.5（中文优化）
    - 向量数据库：ChromaDB（本地持久化）
    - 文本切片：LegalChunker（法律文档专用）
    
    Attributes:
        embedding_model_name: Embedding 模型名称
        persist_directory: ChromaDB 持久化目录
        embedding_model: SentenceTransformer 实例
        chroma_client: ChromaDB 客户端
        collection: ChromaDB 集合
        chunker: 法律文档切片器
    """
    
    # 默认的中文 Embedding 模型
    DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
    
    # ChromaDB 持久化目录
    CHROMA_PERSIST_DIR = "./data/chroma_db"
    
    # ChromaDB 集合名称
    COLLECTION_NAME = "legal_contracts"
    
    def __init__(
        self,
        embedding_model_name: Optional[str] = None,
        persist_directory: Optional[str] = None
    ):
        """
        初始化 RAG 服务
        
        加载 Embedding 模型、初始化 ChromaDB 客户端和集合。
        如果持久化目录不存在，会自动创建。
        
        Args:
            embedding_model_name: Embedding 模型名称，默认使用 bge-small-zh-v1.5
            persist_directory: ChromaDB 持久化目录，默认为 ./data/chroma_db
            
        Raises:
            Exception: 当模型加载或数据库初始化失败时抛出异常
        """
        self.embedding_model_name = embedding_model_name or self.DEFAULT_EMBEDDING_MODEL
        self.persist_directory = persist_directory or self.CHROMA_PERSIST_DIR
        
        try:
            # 确保持久化目录存在
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # 初始化 Embedding 模型
            app_logger.info(f"🔄 正在加载 Embedding 模型: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            app_logger.info(f"✅ Embedding 模型加载完成")
            
            # 初始化 ChromaDB 客户端
            app_logger.info(f"🔄 正在初始化 ChromaDB，持久化目录: {self.persist_directory}")
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 获取或创建集合
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "法律合同文档向量库"}
            )
            
            app_logger.info(f"✅ ChromaDB 初始化完成，集合: {self.COLLECTION_NAME}")
            
            # 初始化法律切片器
            self.chunker = LegalChunker()
            # 初始化 Query Rewrite 与 Reranker
            self.query_rewriter = QueryRewriter()
            self.reranker = Reranker()
            
        except Exception as e:
            app_logger.error(f"❌ RAG 服务初始化失败: {str(e)}")
            raise Exception(f"RAG 服务初始化失败，请检查：\n1. Embedding 模型是否可下载\n2. 磁盘空间是否充足\n错误详情: {str(e)}")
    
    def ingest_contract(
        self,
        text: str,
        contract_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        将合同文本切片并存入向量库
        
        处理流程：
        1. 使用法律切片器进行结构化切片
        2. 生成每个切片的向量表示
        3. 存储到 ChromaDB 中
        
        Args:
            text: 合同全文
            contract_id: 合同唯一标识，如果不提供则自动生成 UUID
            metadata: 额外的元数据（可选），如文件名、上传时间等
            
        Returns:
            Dict: 包含以下字段：
                - contract_id (str): 合同唯一标识
                - chunk_count (int): 切片数量
                - status (str): 状态（success/empty）
                
        Raises:
            Exception: 当向量化或存储失败时抛出异常
        """
        # 生成或使用提供的 contract_id
        if not contract_id:
            contract_id = str(uuid.uuid4())
        
        app_logger.info(f"📥 开始入库合同: {contract_id}")
        
        try:
            # 使用法律切片器进行结构化切片
            chunks = self.chunker.chunk_text(text)
            
            if not chunks:
                app_logger.warning(f"⚠️  合同 {contract_id} 切片结果为空")
                return {
                    "contract_id": contract_id,
                    "chunk_count": 0,
                    "status": "empty"
                }
            
            app_logger.info(f"📊 合同 {contract_id} 共切分为 {len(chunks)} 个片段")
            
            # 生成向量
            app_logger.info(f"🔄 正在生成向量...")
            embeddings = self.embedding_model.encode(
                chunks,
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()
            
            # 准备存储数据
            ids = [f"{contract_id}_{i}" for i in range(len(chunks))]
            
            # 准备元数据
            metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "contract_id": contract_id,
                    "chunk_index": i,
                    "chunk_length": len(chunk)
                }
                
                # 提取章节和条款信息
                legal_metadata = self.chunker.get_chunk_metadata(chunk)
                if legal_metadata.get("chapter"):
                    chunk_metadata["chapter"] = legal_metadata["chapter"]
                if legal_metadata.get("article"):
                    chunk_metadata["article"] = legal_metadata["article"]
                
                # 合并用户提供的额外元数据
                if metadata:
                    chunk_metadata.update(metadata)
                
                metadatas.append(chunk_metadata)
            
            # 存入 ChromaDB
            app_logger.info(f"💾 正在存入向量库...")
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            
            app_logger.info(f"✅ 合同 {contract_id} 入库完成，共 {len(chunks)} 个片段")
            
            return {
                "contract_id": contract_id,
                "chunk_count": len(chunks),
                "status": "success"
            }
            
        except Exception as e:
            app_logger.error(f"❌ 合同 {contract_id} 入库失败: {str(e)}")
            raise Exception(f"合同入库失败: {str(e)}")
    
    async def retrieve_clauses(
        self,
        query: str,
        contract_id: Optional[str] = None,
        top_k: int = 3,
        recall_top_k: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Advanced RAG 检索链路：
        原始 Query -> Query Rewrite -> 向量召回 Top-N -> Rerank 重排 -> 返回 Top-K。
        """
        if not query or not query.strip():
            app_logger.warning("⚠️  查询文本为空")
            return []

        try:
            app_logger.info(
                f"🔍 Advanced 检索开始: {query[:50]}... "
                f"(contract_id: {contract_id}, recall_top_k: {recall_top_k}, top_k: {top_k})"
            )

            rewritten_query = await self.query_rewriter.rewrite(query)
            app_logger.info(f"🧠 Query Rewrite: {query[:30]} -> {rewritten_query[:60]}")

            query_embedding = self.embedding_model.encode(
                [rewritten_query],
                show_progress_bar=False,
                convert_to_numpy=True,
            ).tolist()[0]

            where_filter = None
            if contract_id:
                where_filter = {"contract_id": contract_id}

            raw_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max(recall_top_k, top_k),
                where=where_filter,
            )

            candidates: List[Dict[str, Any]] = []
            if raw_results and raw_results.get("documents") and raw_results["documents"][0]:
                documents = raw_results["documents"][0]
                metadatas = raw_results["metadatas"][0] if raw_results.get("metadatas") else []
                distances = raw_results["distances"][0] if raw_results.get("distances") else []

                for i, doc in enumerate(documents):
                    distance = distances[i] if i < len(distances) else None
                    similarity = (1 - distance) if distance is not None else None
                    candidates.append(
                        {
                            "text": doc,
                            "metadata": metadatas[i] if i < len(metadatas) else {},
                            "distance": distance,
                            "similarity": similarity,
                        }
                    )

            reranked = self.reranker.rerank(
                query=rewritten_query,
                candidates=candidates,
                top_k=top_k,
            )

            app_logger.info(f"✅ Advanced 检索完成，候选 {len(candidates)} -> 返回 {len(reranked)}")
            return reranked

        except Exception as e:
            app_logger.error(f"❌ Advanced 检索失败: {str(e)}")
            raise Exception(f"检索失败: {str(e)}")

    def delete_contract(self, contract_id: str) -> Dict[str, Any]:
        """
        删除指定合同的所有数据
        
        Args:
            contract_id: 合同唯一标识
            
        Returns:
            Dict: 删除结果
        """
        app_logger.info(f"🗑️  删除合同: {contract_id}")
        
        try:
            # 查询该合同的所有文档 ID
            results = self.collection.get(
                where={"contract_id": contract_id}
            )
            
            if results and results["ids"]:
                # 删除所有相关文档
                self.collection.delete(
                    ids=results["ids"]
                )
                deleted_count = len(results["ids"])
                app_logger.info(f"✅ 合同 {contract_id} 删除完成，共删除 {deleted_count} 个片段")
                
                return {
                    "contract_id": contract_id,
                    "deleted_count": deleted_count,
                    "status": "success"
                }
            else:
                app_logger.warning(f"⚠️  合同 {contract_id} 不存在")
                return {
                    "contract_id": contract_id,
                    "deleted_count": 0,
                    "status": "not_found"
                }
        
        except Exception as e:
            app_logger.error(f"❌ 删除合同 {contract_id} 失败: {str(e)}")
            return {
                "contract_id": contract_id,
                "deleted_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    def get_contract_info(self, contract_id: str) -> Dict[str, Any]:
        """
        获取合同的基本信息
        
        Args:
            contract_id: 合同唯一标识
            
        Returns:
            Dict: 合同信息
        """
        results = self.collection.get(
            where={"contract_id": contract_id}
        )
        
        if results and results["ids"]:
            return {
                "contract_id": contract_id,
                "chunk_count": len(results["ids"]),
                "exists": True
            }
        else:
            return {
                "contract_id": contract_id,
                "chunk_count": 0,
                "exists": False
            }
    
    def list_contracts(self) -> List[str]:
        """
        列出所有已存储的合同 ID
        
        Returns:
            List[str]: 合同 ID 列表
        """
        # 获取所有文档的元数据
        results = self.collection.get()
        
        if results and results["metadatas"]:
            # 提取所有唯一的 contract_id
            contract_ids = set()
            for metadata in results["metadatas"]:
                if "contract_id" in metadata:
                    contract_ids.add(metadata["contract_id"])
            
            return sorted(list(contract_ids))
        
        return []


# 全局单例实例（延迟初始化）
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    获取 RAG 服务的全局单例实例
    
    Returns:
        RAGService: RAG 服务实例
    """
    global _rag_service_instance
    
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    
    return _rag_service_instance
