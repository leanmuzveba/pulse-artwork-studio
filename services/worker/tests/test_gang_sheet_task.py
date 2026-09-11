"""Unit tests for the gang_sheets.run task body (storage is monkeypatched, no
broker/MinIO needed)."""

from __future__ import annotations

import io

from PIL import Image

from worker.services import storage
from worker.tasks import gang_sheets


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), (10, 20, 30, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_downloads_each_item_expands_copies_and_uploads_result(monkeypatch):
    monkeypatch.setattr(gang_sheets.run, "update_state", lambda *a, **k: None)

    downloaded = []

    def fake_download(bucket, key):
        downloaded.append((bucket, key))
        return _png(20, 10)

    monkeypatch.setattr(storage, "download_bytes", fake_download)
    uploaded = {}
    monkeypatch.setattr(
        storage,
        "upload_bytes",
        lambda b, k, d, c: uploaded.update(bucket=b, key=k, data=d, content_type=c),
    )

    items = [
        {"artwork_id": "a1", "bucket": "pulse-originals", "key": "a1.png", "copies": 2},
        {"artwork_id": "a2", "bucket": "pulse-originals", "key": "a2.png", "copies": 1},
    ]
    result = gang_sheets.run.run(
        "gs-1", "proj-1", sheet_width_px=300, spacing_px=5, dpi=300, items=items
    )

    # One download call per item (not per copy) — copies are expanded from
    # the single downloaded image.
    assert downloaded == [("pulse-originals", "a1.png"), ("pulse-originals", "a2.png")]
    assert uploaded["bucket"] == "pulse-exports"
    assert uploaded["key"] == "projects/proj-1/gang-sheets/gs-1.png"
    assert uploaded["content_type"] == "image/png"

    assert result["bucket"] == "pulse-exports"
    assert result["key"] == uploaded["key"]
    assert result["sheet_width_px"] == 300
    assert result["dpi"] == 300
    # 2 copies of a1 + 1 of a2 = 3 placements.
    assert len(result["placements"]) == 3
    assert [p["artwork_id"] for p in result["placements"]] == ["a1", "a1", "a2"]


def test_result_image_dimensions_match_the_reported_sheet_size(monkeypatch):
    monkeypatch.setattr(gang_sheets.run, "update_state", lambda *a, **k: None)
    monkeypatch.setattr(storage, "download_bytes", lambda bucket, key: _png(20, 10))
    uploaded = {}
    monkeypatch.setattr(
        storage, "upload_bytes", lambda b, k, d, c: uploaded.update(data=d)
    )

    items = [{"artwork_id": "a1", "bucket": "b", "key": "k", "copies": 1}]
    result = gang_sheets.run.run(
        "gs-2", "proj-1", sheet_width_px=100, spacing_px=5, dpi=150, items=items
    )

    img = Image.open(io.BytesIO(uploaded["data"]))
    assert img.size == (100, result["sheet_height_px"])
