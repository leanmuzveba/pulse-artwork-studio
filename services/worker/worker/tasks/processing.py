"""Artwork processing tasks.

The worker is deliberately stateless: it downloads the source object, computes a
result, and returns it via Celery's result backend. The API reconciles that
result into the processing_jobs row when the client polls job status — so the
worker never needs database access.

Operations that produce a new image upload their output to the derived-assets
bucket themselves and return its location; the API turns that into a new
derived `Artwork` row on reconcile. `metadata` and `dtf_check` are analysis-only
— they return a result dict but no image, so the API annotates the artwork
being inspected instead of creating a derived one.
"""

from __future__ import annotations

from typing import Any

from worker.celery_app import celery_app
from worker.config import get_settings
from worker.services import imaging, storage

SUPPORTED_OPERATIONS = {
    "metadata",
    "enhance",
    "upscale",
    "background_removal",
    "halftone",
    "embroidery",
    "vectorize",
    "dtf_check",
    "crop",
    "rotate",
    "flip",
    "resize",
    "underbase_preview",
}

# Operations that analyze the image and return a result dict, no image output.
_ANALYSES = {
    "metadata": lambda data, parameters: imaging.extract_metadata(data),
    "dtf_check": imaging.dtf_check,
}

# Operations that transform the image and need their output persisted.
_TRANSFORMS = {
    "enhance": imaging.enhance,
    "upscale": imaging.upscale,
    "background_removal": imaging.remove_background,
    "halftone": imaging.halftone,
    "embroidery": imaging.embroidery,
    "vectorize": imaging.vectorize,
    "crop": imaging.crop,
    "rotate": imaging.rotate,
    "flip": imaging.flip,
    "resize": imaging.resize,
    "underbase_preview": imaging.underbase_preview,
}

# Each transform's output format — most produce a raster PNG, but vectorize
# produces vector SVG markup, which has no fixed pixel dimensions.
_TRANSFORM_OUTPUT: dict[str, tuple[str, str]] = {
    "enhance": ("png", "image/png"),
    "upscale": ("png", "image/png"),
    "background_removal": ("png", "image/png"),
    "halftone": ("png", "image/png"),
    "embroidery": ("png", "image/png"),
    "vectorize": ("svg", "image/svg+xml"),
    "crop": ("png", "image/png"),
    "rotate": ("png", "image/png"),
    "flip": ("png", "image/png"),
    "resize": ("png", "image/png"),
    "underbase_preview": ("png", "image/png"),
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

    if operation in _ANALYSES:
        return _ANALYSES[operation](data, parameters or {})

    output = _TRANSFORMS[operation](data, parameters or {})
    ext, mime_type = _TRANSFORM_OUTPUT[operation]

    settings = get_settings()
    out_bucket = settings.s3_bucket_derived
    out_key = f"projects/{project_id}/derived/{job_id}/{operation}.{ext}"
    storage.upload_bytes(out_bucket, out_key, output, mime_type)

    if ext == "png":
        result = imaging.extract_metadata(output)
    else:
        # Vector output (e.g. vectorize's SVG) — no fixed pixel size to report.
        result = {"width": None, "height": None}

    result.update(bucket=out_bucket, key=out_key, mime_type=mime_type, size_bytes=len(output))
    return result
