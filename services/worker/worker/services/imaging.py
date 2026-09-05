"""Image analysis and transform helpers. Pure functions — no Celery/DB imports,
easy to test in isolation."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageEnhance, ImageOps

# Upscale is capped to avoid a single job exhausting worker memory/CPU.
MAX_UPSCALE_FACTOR = 4.0
MAX_UPSCALE_DIMENSION = 8000


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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


def enhance(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Auto-enhance an image: contrast stretch plus a mild sharpen/contrast/color
    boost. Transparency (if any) is preserved untouched — only RGB is adjusted.

    Optional `parameters`: `sharpness`, `contrast`, `color` — multipliers around
    1.0, each clamped to [0.5, 2.0].
    """
    parameters = parameters or {}
    sharpness = _clamp(float(parameters.get("sharpness", 1.3)), 0.5, 2.0)
    contrast = _clamp(float(parameters.get("contrast", 1.1)), 0.5, 2.0)
    color = _clamp(float(parameters.get("color", 1.05)), 0.5, 2.0)

    with Image.open(BytesIO(data)) as img:
        img.load()
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        rgba = img.convert("RGBA")
        rgb = rgba.convert("RGB")
        alpha = rgba.getchannel("A")

        rgb = ImageOps.autocontrast(rgb, cutoff=1)
        rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
        rgb = ImageEnhance.Color(rgb).enhance(color)
        rgb = ImageEnhance.Sharpness(rgb).enhance(sharpness)

        out = BytesIO()
        if has_alpha:
            result = rgb.convert("RGBA")
            result.putalpha(alpha)
            result.save(out, format="PNG")
        else:
            rgb.save(out, format="PNG")
        return out.getvalue()


def upscale(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Upscale an image with high-quality (Lanczos) resampling.

    Optional `parameters.scale` (default 2.0) multiplies both dimensions,
    clamped to [1.0, `MAX_UPSCALE_FACTOR`]; the output is additionally capped at
    `MAX_UPSCALE_DIMENSION` px per side regardless of the requested scale.
    """
    parameters = parameters or {}
    scale = _clamp(float(parameters.get("scale", 2.0)), 1.0, MAX_UPSCALE_FACTOR)

    with Image.open(BytesIO(data)) as img:
        img.load()
        target_w = min(round(img.width * scale), MAX_UPSCALE_DIMENSION)
        target_h = min(round(img.height * scale), MAX_UPSCALE_DIMENSION)
        resized = img.resize((max(target_w, 1), max(target_h, 1)), Image.LANCZOS)

        out = BytesIO()
        resized.save(out, format="PNG")
        return out.getvalue()
