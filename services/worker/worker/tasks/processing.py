"""Artwork processing tasks.

The worker is deliberately stateless: it downloads the source object, computes a
result, and returns it via Celery's result backend. The API reconciles that
result into the processing_jobs row when the client polls job status — so the
worker never needs database access.

Operations that produce a new image (everything but `metadata`) upload their
output to the derived-assets bucket themselves and return its location; the API
turns that into a new derived `Artwork` row on reconcile.
"""

from __future__ import annotations

from typing import Any

from worker.celery_app import celery_app
from worker.config import get_settings
from worker.services import imaging, storage

SUPPORTED_OPERATIONS = {"metadata", "enhance", "upscale", "background_removal"}

# Operations that transform the image and need their output persisted.
_TRANSFORMS = {
    "enhance": imaging.enhance,
    "upscale": imaging.upscale,
    "background_removal": imaging.remove_background,
}


@celery_app.task(name="processing.run", bind=True)
def run(
    self,
    job_id: str,
    operation: str,
    bucket: str,
    key: str,
    parameters: dict[str, Any] | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Run a processing operation on a stored artwork and return its result."""
    if operation not in SUPPORTED_OPERATIONS:
        raise ValueError(f"Unsupported operation: {operation!r}")

    self.update_state(state="STARTED", meta={"job_id": job_id, "operation": operation})
    data = storage.download_bytes(bucket, key)

    if operation == "metadata":
        return imaging.extract_metadata(data)

    output = _TRANSFORMS[operation](data, parameters or {})
    result = imaging.extract_metadata(output)

    settings = get_settings()
    out_bucket = settings.s3_bucket_derived
    out_key = f"projects/{project_id}/derived/{job_id}/{operation}.png"
    storage.upload_bytes(out_bucket, out_key, output, "image/png")

    result.update(bucket=out_bucket, key=out_key, mime_type="image/png", size_bytes=len(output))
    return result
