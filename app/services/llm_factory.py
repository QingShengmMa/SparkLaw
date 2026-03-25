"""
兼容层：从新分层路径重新导出 LLMFactory。
实际实现已迁移至 app/llm/factory.py
"""
from app.llm.factory import LLMFactory

__all__ = ["LLMFactory"]
