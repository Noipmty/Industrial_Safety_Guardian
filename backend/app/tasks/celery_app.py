"""Celery 应用（Redis broker + backend）。

启动 worker：
    conda run -n jrong python -m celery -A app.tasks.celery_app worker -l info
启动每日 beat 调度器：
    conda run -n jrong python -m celery -A app.tasks.celery_app beat -l info
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gongan_weishi",
    broker=settings.redis.url,
    backend=settings.redis.url,
    include=["app.tasks.ingest", "app.tasks.memory_decay"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    # Prompt §P1：每日 0.98 衰减 + 清理已遗忘的记忆。
    "decay-memories-daily": {
        "task": "app.tasks.memory_decay.decay_memories",
        "schedule": crontab(hour=3, minute=0),
    },
}
