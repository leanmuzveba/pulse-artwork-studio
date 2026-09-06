"""Export rendering tasks.

Mirrors processing.py's design: the worker is stateless — it downloads the
source object, renders the requested format, uploads the result, and returns
its location. The API reconciles that into the exports row on poll.
"""

from __future__ import annotations

from typing import Any

from worker.celery_app import celery_app
from worker.config import get_settings
from worker.services import imaging, storage

SUPPORTED_FORMATS = {"png", "pdf", "svg"}

_EXTENSIONS = {"png": "png", "pdf": "pdf", "svg": "svg"}
_MIME_TYPES = {"png": "image/png", "pdf": "application/pdf", "svg": "image/svg+xml"}

_RENDERERS = {
    "png": imaging.export_png,
    "pdf": imaging.export_pdf,
    "svg": imaging.vectorize,
}


@celery_app.task(name="exports.run", bind=True)
def run(
    self,
    export_id: str,
    format: str,
    bucket: str,
    key: str,
    parameters: dict[str, Any] | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Render a stored artwork into the requested export format."""
    if format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported export format: {format!r}")

    self.update_state(state="STARTED", meta={"export_id": export_id, "format": format})
    data = storage.download_bytes(bucket, key)
    parameters = parameters or {}
    output = _RENDERERS[format](data, parameters)

    settings = get_settings()
    out_bucket = settings.s3_bucket_exports
    out_key = f"projects/{project_id}/exports/{export_id}.{_EXTENSIONS[format]}"
    mime_type = _MIME_TYPES[format]
    storage.upload_bytes(out_bucket, out_key, output, mime_type)

    result: dict[str, Any] = {
        "bucket": out_bucket,
        "key": out_key,
        "mime_type": mime_type,
        "size_bytes": len(output),
        "width": None,
        "height": None,
        "dpi": None,
    }
    if format == "png":
        # The output is a real PNG — read its (possibly resized) dimensions
        # and embedded DPI straight back off it.
        meta = imaging.extract_metadata(output)
        result["width"] = meta["width"]
        result["height"] = meta["height"]
        result["dpi"] = meta["source_dpi"]
    elif format == "pdf":
        # Pillow can only write PDFs, not read them back — export_pdf doesn't
        # resize, so the source image's dimensions still apply; DPI is
        # whatever we asked Pillow to embed.
        meta = imaging.extract_metadata(data)
        result["width"] = meta["width"]
        result["height"] = meta["height"]
        result["dpi"] = int(parameters.get("dpi", 300))
    # SVG is vector output — there's no fixed pixel size or DPI to report.
    return result
