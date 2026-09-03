"""Image analysis helpers. Pure functions — no Celery/DB imports, easy to test."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image


def extract_metadata(data: bytes) -> dict[str, Any]:
    """Read basic image metadata from raw bytes.

    Returns width/height in pixels, the format and mode, whether the image has
    an alpha channel (transparency), and the embedded DPI if present.
    """
    with Image.open(BytesIO(data)) as img:
        dpi = img.info.get("dpi")
        source_dpi = int(round(dpi[0])) if dpi else None
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "has_alpha": bool(has_alpha),
            "source_dpi": source_dpi,
        }
