"""
兼容层：从新分层路径重新导出 QueryRewriter。
实际实现已迁移至 app/knowledge/retrievers/query_rewriter.py
"""
from app.knowledge.retrievers.query_rewriter import QueryRewriter

__all__ = ["QueryRewriter"]
