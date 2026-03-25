"""
兼容层：重新导出文档路由。
实际实现在 app/api/v1/routes/document.py
"""
from app.api.v1.routes.document import router

__all__ = ["router"]
