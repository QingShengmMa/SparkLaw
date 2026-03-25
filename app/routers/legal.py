"""
兼容层：重新导出法律咨询路由。
实际实现在 app/api/v1/routes/chat.py
"""
from app.api.v1.routes.chat import router

__all__ = ["router"]
