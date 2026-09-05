"""Unit tests for image processing helpers (needs Pillow, no broker/DB)."""

from __future__ import annotations

import io

from PIL import Image

from worker.services.imaging import enhance, extract_metadata, upscale


def _png(width: int, height: int, mode: str = "RGBA") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, (width, height), (255, 0, 0, 255) if mode == "RGBA" else 0).save(
        buf, format="PNG"
    )
    return buf.getvalue()


def test_extract_metadata_reads_dimensions_and_alpha():
    meta = extract_metadata(_png(120, 80, "RGBA"))
    assert meta["width"] == 120
    assert meta["height"] == 80
    assert meta["format"] == "PNG"
    assert meta["has_alpha"] is True


def test_extract_metadata_no_alpha_for_rgb():
    meta = extract_metadata(_png(10, 10, "RGB"))
    assert meta["has_alpha"] is False


def test_upscale_doubles_dimensions_by_default():
    out = upscale(_png(10, 20, "RGB"), {})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (20, 40)


def test_upscale_scale_factor_is_clamped():
    out = upscale(_png(10, 10, "RGB"), {"scale": 100})
    meta = extract_metadata(out)
    assert meta["width"] == meta["height"] == 40  # clamped to MAX_UPSCALE_FACTOR (4x)


def test_enhance_preserves_dimensions_and_alpha():
    out = enhance(_png(50, 50, "RGBA"), {})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (50, 50)
    assert meta["has_alpha"] is True


def test_enhance_preserves_opaque_mode():
    out = enhance(_png(50, 50, "RGB"), {})
    meta = extract_metadata(out)
    assert meta["has_alpha"] is False
