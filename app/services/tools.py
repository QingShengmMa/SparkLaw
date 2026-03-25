"""
兼容层：从新分层路径重新导出工具函数。
实际实现已迁移至 app/tools/legal_tools.py
"""
from app.tools.legal_tools import calculate_labor_compensation, search_latest_legal_cases, get_tools

__all__ = ["calculate_labor_compensation", "search_latest_legal_cases", "get_tools"]
