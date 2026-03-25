"""
Celery application configuration.
Moved from app/celery_app.py to app/workers/celery_app.py.
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
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

__all__ = ["celery_app"]
