"""
兼容层：重新导出健康检查路由。
实际实现在 app/api/v1/routes/health.py
"""
from app.api.v1.routes.health import router

__all__ = ["router"]
