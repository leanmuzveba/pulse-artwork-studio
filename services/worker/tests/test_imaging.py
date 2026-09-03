"""Unit tests for image metadata extraction (needs Pillow, no broker/DB)."""

from __future__ import annotations

import io

from PIL import Image

from worker.services.imaging import extract_metadata


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
