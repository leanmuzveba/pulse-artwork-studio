"""Unit tests for the storage service (presigning is offline — no MinIO needed)."""

from __future__ import annotations

import uuid

from app.services import storage


def test_sanitize_filename_strips_path_and_unsafe_chars():
    assert storage.sanitize_filename("../../etc/pass wd!.PNG") == "pass_wd_.PNG"
    assert "/" not in storage.sanitize_filename("a/b/c.png")


def test_build_original_key_layout():
    pid, aid = uuid.uuid4(), uuid.uuid4()
    key = storage.build_original_key(pid, aid, "logo.png")
    assert key == f"projects/{pid}/originals/{aid}/logo.png"


def test_presigned_upload_url_is_signed_and_scoped():
    url = storage.create_presigned_upload(
        "pulse-originals", "projects/p/originals/a/logo.png", "image/png", 900
    )
    assert "projects/p/originals/a/logo.png" in url
    assert "X-Amz-Signature=" in url
    assert "X-Amz-Expires=900" in url


def test_presigned_download_url_is_signed():
    url = storage.create_presigned_download("pulse-originals", "some/key.png", 600)
    assert "X-Amz-Signature=" in url
    assert "X-Amz-Expires=600" in url
