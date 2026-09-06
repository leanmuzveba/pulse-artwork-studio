"""Image analysis and transform helpers. Pure functions — no Celery/DB imports,
easy to test in isolation."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from typing import Any

import rembg
import vtracer
from PIL import Image, ImageEnhance, ImageOps

# Upscale is capped to avoid a single job exhausting worker memory/CPU.
MAX_UPSCALE_FACTOR = 4.0
MAX_UPSCALE_DIMENSION = 8000

# DTF print-readiness thresholds.
DTF_RECOMMENDED_DPI = 300
DTF_MIN_ACCEPTABLE_DPI = 150
DTF_MIN_DIMENSION_PX = 100


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


def dtf_check(data: bytes, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Analyze an artwork for DTF print-readiness (the "AI Inspector").

    Analysis only — no image is produced. Optional `parameters.target_width_in`
    / `target_height_in` (inches) let the effective print DPI be computed from
    the intended print size; otherwise the file's embedded DPI is used.

    Returns the base metadata plus `effective_dpi`, a `checks` list of
    `{code, severity, message}` (severity "warning" or "error"), and an overall
    `ready` flag (false if any check is an "error").
    """
    parameters = parameters or {}
    meta = extract_metadata(data)

    effective_dpi = meta["source_dpi"]
    target_width_in = parameters.get("target_width_in")
    target_height_in = parameters.get("target_height_in")
    if target_width_in:
        effective_dpi = round(meta["width"] / float(target_width_in))
    elif target_height_in:
        effective_dpi = round(meta["height"] / float(target_height_in))

    checks: list[dict[str, str]] = []

    if effective_dpi is not None and effective_dpi < DTF_MIN_ACCEPTABLE_DPI:
        checks.append(
            {
                "code": "low_resolution",
                "severity": "error",
                "message": f"Effective resolution is {effective_dpi} DPI; "
                f"DTF printing needs at least {DTF_MIN_ACCEPTABLE_DPI} DPI.",
            }
        )
    elif effective_dpi is not None and effective_dpi < DTF_RECOMMENDED_DPI:
        checks.append(
            {
                "code": "low_resolution",
                "severity": "warning",
                "message": f"Effective resolution is {effective_dpi} DPI; "
                f"{DTF_RECOMMENDED_DPI} DPI is recommended for crisp DTF prints.",
            }
        )

    if not meta["has_alpha"]:
        checks.append(
            {
                "code": "no_transparency",
                "severity": "warning",
                "message": "No transparency detected — run background removal "
                "before printing, unless a full-bleed background is intended.",
            }
        )

    if meta["mode"] not in ("RGB", "RGBA"):
        checks.append(
            {
                "code": "unsupported_color_mode",
                "severity": "warning",
                "message": f"Image is in {meta['mode']} mode; convert to RGB/RGBA.",
            }
        )

    if meta["width"] < DTF_MIN_DIMENSION_PX or meta["height"] < DTF_MIN_DIMENSION_PX:
        checks.append(
            {
                "code": "image_too_small",
                "severity": "error",
                "message": f"Image is {meta['width']}x{meta['height']}px; "
                f"at least {DTF_MIN_DIMENSION_PX}x{DTF_MIN_DIMENSION_PX}px is needed.",
            }
        )

    ready = not any(c["severity"] == "error" for c in checks)
    return {**meta, "effective_dpi": effective_dpi, "checks": checks, "ready": ready}


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


@lru_cache(maxsize=1)
def _background_removal_session():
    """Load the U^2-Net model once per worker process and reuse it across jobs."""
    return rembg.new_session("u2net")


def remove_background(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Remove the background, producing a transparent PNG (via rembg/U^2-Net).

    Optional `parameters.alpha_matting` (bool, default False) trades speed for
    softer edges on foreground objects with fine detail (hair, fur).
    """
    parameters = parameters or {}
    alpha_matting = bool(parameters.get("alpha_matting", False))
    return rembg.remove(
        data, session=_background_removal_session(), alpha_matting=alpha_matting
    )


def vectorize(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Trace a raster image into a real path-based SVG (via vtracer).

    The input is normalized to RGBA PNG first (vtracer needs a raw pixel
    format it understands), then traced. Optional `parameters`: `mode`
    ("spline", "polygon", or "none"; default "spline"), `color_precision`
    (default 6), `filter_speckle` (default 4, suppresses tiny noise regions).

    Returns UTF-8-encoded SVG markup, not a raster image.
    """
    parameters = parameters or {}
    mode = parameters.get("mode", "spline")
    color_precision = int(parameters.get("color_precision", 6))
    filter_speckle = int(parameters.get("filter_speckle", 4))

    with Image.open(BytesIO(data)) as img:
        img.load()
        png_buf = BytesIO()
        img.convert("RGBA").save(png_buf, format="PNG")
        png_bytes = png_buf.getvalue()

    svg = vtracer.convert_raw_image_to_svg(
        png_bytes,
        img_format="png",
        mode=mode,
        color_precision=color_precision,
        filter_speckle=filter_speckle,
    )
    return svg.encode("utf-8")
