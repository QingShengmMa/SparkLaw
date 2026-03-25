"""
兼容层：从新分层路径重新导出 RAGService 与 get_rag_service。
实际实现已迁移至 app/knowledge/rag_service.py
"""
from app.knowledge.rag_service import RAGService, get_rag_service

__all__ = ["RAGService", "get_rag_service"]
