"""Unit tests for the exports.run task body (storage is monkeypatched, no
broker/MinIO needed; vtracer's native call is monkeypatched for the SVG case
— see test_imaging.py for why)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from worker.services import imaging, storage
from worker.tasks import exports


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), (10, 20, 30, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_png_export_uploads_result_and_returns_dimensions(monkeypatch):
    monkeypatch.setattr(exports.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(10, 10))
    uploaded = {}

    def fake_upload(bucket, key, data, content_type):
        uploaded.update(bucket=bucket, key=key, data=data, content_type=content_type)

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    result = exports.run.run(
        "exp-1", "png", "pulse-originals", "src.png", {}, "proj-1"
    )

    assert uploaded["bucket"] == "pulse-exports"
    assert uploaded["key"] == "projects/proj-1/exports/exp-1.png"
    assert uploaded["content_type"] == "image/png"
    assert result["width"] == 10 and result["height"] == 10
    assert result["dpi"] == 300  # export_png's default


def test_pdf_export_uploads_result(monkeypatch):
    monkeypatch.setattr(exports.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(10, 10))
    uploaded = {}

    def fake_upload(bucket, key, data, content_type):
        uploaded.update(bucket=bucket, key=key, data=data, content_type=content_type)

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    result = exports.run.run(
        "exp-2", "pdf", "pulse-originals", "src.png", {}, "proj-1"
    )

    assert uploaded["bucket"] == "pulse-exports"
    assert uploaded["key"] == "projects/proj-1/exports/exp-2.pdf"
    assert uploaded["content_type"] == "application/pdf"
    # Pillow can't read PDFs back, so dims come from the source image instead.
    assert result["width"] == 10 and result["height"] == 10
    assert result["dpi"] == 300


def test_svg_export_has_no_pixel_dimensions(monkeypatch):
    monkeypatch.setattr(exports.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(10, 10))
    monkeypatch.setattr(
        imaging.vtracer, "convert_raw_image_to_svg", lambda *a, **k: "<svg/>"
    )
    uploaded = {}

    def fake_upload(bucket, key, data, content_type):
        uploaded.update(bucket=bucket, key=key, data=data, content_type=content_type)

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    result = exports.run.run(
        "exp-3", "svg", "pulse-originals", "src.png", {}, "proj-1"
    )

    assert uploaded["bucket"] == "pulse-exports"
    assert uploaded["key"] == "projects/proj-1/exports/exp-3.svg"
    assert uploaded["content_type"] == "image/svg+xml"
    assert uploaded["data"] == b"<svg/>"
    assert result["width"] is None and result["dpi"] is None


def test_unsupported_format_raises():
    with pytest.raises(ValueError):
        exports.run.run("exp-4", "gif", "b", "k")
