"""Unit tests for the processing.run task body (storage is monkeypatched, no
broker/MinIO needed)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from worker.services import imaging, storage
from worker.tasks import processing


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), (10, 20, 30, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_metadata_op_does_not_touch_storage_writes(monkeypatch):
    monkeypatch.setattr(processing.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(5, 5))
    monkeypatch.setattr(
        storage, "upload_bytes", lambda *a, **k: pytest.fail("metadata should not upload")
    )

    result = processing.run.run("job-1", "metadata", "b", "k")
    assert result["width"] == 5 and result["height"] == 5


def test_upscale_op_uploads_result_and_returns_location(monkeypatch):
    monkeypatch.setattr(processing.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(10, 10))
    uploaded = {}

    def fake_upload(bucket, key, data, content_type):
        uploaded.update(bucket=bucket, key=key, data=data, content_type=content_type)

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    result = processing.run.run(
        "job-2", "upscale", "pulse-originals", "src.png", {"scale": 2}, "proj-1"
    )

    assert uploaded["bucket"] == "pulse-derived"
    assert uploaded["key"] == "projects/proj-1/derived/job-2/upscale.png"
    assert uploaded["content_type"] == "image/png"
    assert result["bucket"] == "pulse-derived"
    assert result["key"] == uploaded["key"]
    assert result["width"] == 20 and result["height"] == 20


def test_background_removal_op_uploads_result_and_returns_location(monkeypatch):
    # background_removal's transform is rembg (real model) — swap it out here so
    # this test exercises the task's dispatch/upload plumbing, not segmentation.
    monkeypatch.setattr(processing.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(10, 10))
    monkeypatch.setitem(
        processing._TRANSFORMS, "background_removal", lambda data, params: _png(10, 10)
    )
    uploaded = {}

    def fake_upload(bucket, key, data, content_type):
        uploaded.update(bucket=bucket, key=key, data=data, content_type=content_type)

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    result = processing.run.run(
        "job-4", "background_removal", "pulse-originals", "src.png", {}, "proj-2"
    )

    assert uploaded["bucket"] == "pulse-derived"
    assert uploaded["key"] == "projects/proj-2/derived/job-4/background_removal.png"
    assert result["bucket"] == "pulse-derived"


def test_dtf_check_op_does_not_touch_storage_writes(monkeypatch):
    monkeypatch.setattr(processing.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(50, 50))
    monkeypatch.setattr(
        storage, "upload_bytes", lambda *a, **k: pytest.fail("dtf_check should not upload")
    )

    result = processing.run.run("job-5", "dtf_check", "b", "k")
    assert "checks" in result and "ready" in result


def test_halftone_op_uploads_result_and_returns_location(monkeypatch):
    monkeypatch.setattr(processing.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(10, 10))
    uploaded = {}

    def fake_upload(bucket, key, data, content_type):
        uploaded.update(bucket=bucket, key=key, data=data, content_type=content_type)

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    result = processing.run.run(
        "job-6", "halftone", "pulse-originals", "src.png", {}, "proj-3"
    )

    assert uploaded["bucket"] == "pulse-derived"
    assert uploaded["key"] == "projects/proj-3/derived/job-6/halftone.png"
    assert uploaded["content_type"] == "image/png"
    assert result["width"] == 10 and result["height"] == 10


def test_embroidery_op_uploads_result_and_returns_location(monkeypatch):
    monkeypatch.setattr(processing.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(10, 10))
    uploaded = {}

    def fake_upload(bucket, key, data, content_type):
        uploaded.update(bucket=bucket, key=key, data=data, content_type=content_type)

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    result = processing.run.run(
        "job-7", "embroidery", "pulse-originals", "src.png", {}, "proj-3"
    )

    assert uploaded["bucket"] == "pulse-derived"
    assert uploaded["key"] == "projects/proj-3/derived/job-7/embroidery.png"
    assert result["width"] == 10 and result["height"] == 10


def test_vectorize_op_uploads_svg_with_no_pixel_dimensions(monkeypatch):
    # vectorize's transform is vtracer (a native call that segfaults on this
    # machine's Python 3.14, see project memory) — swap it out here so this
    # test exercises the task's dispatch/upload plumbing, not real tracing.
    monkeypatch.setattr(processing.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(10, 10))
    monkeypatch.setattr(
        imaging.vtracer, "convert_raw_image_to_svg", lambda *a, **k: "<svg/>"
    )
    uploaded = {}

    def fake_upload(bucket, key, data, content_type):
        uploaded.update(bucket=bucket, key=key, data=data, content_type=content_type)

    monkeypatch.setattr(storage, "upload_bytes", fake_upload)

    result = processing.run.run(
        "job-8", "vectorize", "pulse-originals", "src.png", {}, "proj-3"
    )

    assert uploaded["bucket"] == "pulse-derived"
    assert uploaded["key"] == "projects/proj-3/derived/job-8/vectorize.svg"
    assert uploaded["content_type"] == "image/svg+xml"
    assert uploaded["data"] == b"<svg/>"
    assert result["width"] is None and result["height"] is None
    assert result["mime_type"] == "image/svg+xml"


def test_unsupported_operation_raises():
    with pytest.raises(ValueError):
        processing.run.run("job-3", "not-a-real-op", "b", "k")
