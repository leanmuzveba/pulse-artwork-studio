"""System tasks used to verify the queue end-to-end.

These prove the API -> Redis -> worker -> result round-trip works before any real
image processing exists. Real processors (metadata, enhancement, background
removal, ...) land in Phase 2 as sibling modules under ``worker/tasks/``.
"""

from __future__ import annotations

from typing import Any

from worker.celery_app import celery_app


@celery_app.task(name="system.ping")
def ping() -> str:
    """Liveness check for the worker fleet."""
    return "pong"


@celery_app.task(name="system.echo")
def echo(payload: Any) -> dict[str, Any]:
    """Return the payload back — used to smoke-test enqueue + result delivery."""
    return {"echo": payload}
