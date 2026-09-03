"""Celery application.

Start a worker:
    celery -A worker.celery_app worker --loglevel=info
"""

from __future__ import annotations

from celery import Celery

from worker.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pulse",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks.system", "worker.tasks.processing"],
)

celery_app.conf.update(
    task_track_started=True,        # emit a STARTED state so the API can show "processing"
    task_acks_late=True,            # re-deliver if a worker dies mid-task
    worker_prefetch_multiplier=1,   # fair dispatch for long image/AI jobs
    result_expires=3600,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
