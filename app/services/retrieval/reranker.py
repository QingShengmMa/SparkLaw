"""
兼容层：从新分层路径重新导出 Reranker。
实际实现已迁移至 app/knowledge/rerankers/cross_encoder.py
"""
from app.knowledge.rerankers.cross_encoder import Reranker

__all__ = ["Reranker"]
