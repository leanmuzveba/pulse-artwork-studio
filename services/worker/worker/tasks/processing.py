"""Artwork processing tasks.

The worker is deliberately stateless: it downloads the source object, computes a
result, and returns it via Celery's result backend. The API reconciles that
result into the processing_jobs row when the client polls job status — so the
worker never needs database access.
"""

from __future__ import annotations

from typing import Any

from worker.celery_app import celery_app
from worker.services import imaging, storage

SUPPORTED_OPERATIONS = {"metadata"}


@celery_app.task(name="processing.run", bind=True)
def run(
    self,
    job_id: str,
    operation: str,
    bucket: str,
    key: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a processing operation on a stored artwork and return its result."""
    if operation not in SUPPORTED_OPERATIONS:
        raise ValueError(f"Unsupported operation: {operation!r}")

    self.update_state(state="STARTED", meta={"job_id": job_id, "operation": operation})
    data = storage.download_bytes(bucket, key)

    if operation == "metadata":
        return imaging.extract_metadata(data)

    # Unreachable given the guard above; keeps type checkers happy.
    raise ValueError(f"Unsupported operation: {operation!r}")
