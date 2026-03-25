"""
兼容层：重新导出智能分析路由。
实际实现在 app/api/v1/routes/tools.py
"""
from app.api.v1.routes.tools import router

__all__ = ["router"]
