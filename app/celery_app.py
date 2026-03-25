"""
兼容层：从新路径重新导出 celery_app。
实际实现已迁移至 app/workers/celery_app.py
"""
from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
