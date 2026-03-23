"""
Celery 应用配置
使用 Redis 作为 Broker 和 Result Backend
"""

from celery import Celery
from app.core.config import settings


celery_app = Celery(
    "sparklaw",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.services.multimodal_contract_reviewer"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
)
