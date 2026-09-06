"""API-side Celery client.

Enqueues tasks by name (no import dependency on the worker package) and reads
task state back for reconciliation. Kept as thin module-level functions so tests
can monkeypatch them without a live broker.
"""

from __future__ import annotations

import uuid
from typing import Any

from celery import Celery
from celery.result import AsyncResult

from app.core.config import get_settings

settings = get_settings()

_celery = Celery(
    "pulse-api",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

TASK_RUN = "processing.run"
TASK_EXPORT = "exports.run"


def enqueue_job(
    operation: str,
    job_id: uuid.UUID,
    bucket: str,
    key: str,
    parameters: dict[str, Any],
    project_id: uuid.UUID,
) -> str:
    """Publish a processing task and return its Celery task id."""
    result = _celery.send_task(
        TASK_RUN,
        kwargs={
            "job_id": str(job_id),
            "operation": operation,
            "bucket": bucket,
            "key": key,
            "parameters": parameters,
            "project_id": str(project_id),
        },
    )
    return result.id


def enqueue_export(
    export_id: uuid.UUID,
    export_format: str,
    bucket: str,
    key: str,
    parameters: dict[str, Any],
    project_id: uuid.UUID,
) -> str:
    """Publish an export task and return its Celery task id."""
    result = _celery.send_task(
        TASK_EXPORT,
        kwargs={
            "export_id": str(export_id),
            "format": export_format,
            "bucket": bucket,
            "key": key,
            "parameters": parameters,
            "project_id": str(project_id),
        },
    )
    return result.id


def get_job_state(task_id: str) -> tuple[str, Any]:
    """Return (celery_state, result). States: PENDING/STARTED/SUCCESS/FAILURE/..."""
    res = AsyncResult(task_id, app=_celery)
    return res.state, res.result
