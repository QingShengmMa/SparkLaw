"""
兼容层：模拟法庭路由适配器。
实际庭审 SSE 端点在 app/api/v1/routes/tools.py 的 /debate/court。
"""
from app.api.v1.routes.tools import router

__all__ = ["router"]
