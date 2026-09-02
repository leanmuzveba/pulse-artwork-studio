"""Integration tests for projects + the signed-URL upload flow.

- Project CRUD and the upload-url request need only PostgreSQL (presigning is
  offline), so they run whenever a DB is available.
- The full PUT-to-storage + confirm path also needs object storage, so it is
  additionally gated on `require_storage`.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# 1x1 transparent PNG
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _auth_headers() -> dict[str, str]:
    email = f"user-{uuid.uuid4().hex[:12]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "pw-123456"})
    tok = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pw-123456"}
    ).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.mark.usefixtures("require_db")
def test_projects_require_auth():
    assert client.get("/api/v1/projects").status_code == 401
    assert client.post("/api/v1/projects", json={"name": "x"}).status_code == 401


@pytest.mark.usefixtures("require_db")
def test_project_crud_and_upload_url():
    headers = _auth_headers()

    # Create + list + get
    created = client.post("/api/v1/projects", json={"name": "Summer Tees"}, headers=headers)
    assert created.status_code == 201, created.text
    pid = created.json()["data"]["id"]

    listed = client.get("/api/v1/projects", headers=headers).json()["data"]
    assert any(p["id"] == pid for p in listed)
    assert client.get(f"/api/v1/projects/{pid}", headers=headers).status_code == 200

    # Unsupported file type is rejected (415)
    bad = client.post(
        f"/api/v1/projects/{pid}/artworks/upload-url",
        json={"filename": "art.tiff", "content_type": "image/tiff"},
        headers=headers,
    )
    assert bad.status_code == 415

    # Request an upload URL for a PNG
    up = client.post(
        f"/api/v1/projects/{pid}/artworks/upload-url",
        json={"filename": "logo.png", "content_type": "image/png", "size_bytes": len(_PNG)},
        headers=headers,
    )
    assert up.status_code == 201, up.text
    data = up.json()["data"]
    assert data["upload_url"].startswith("http")
    assert data["storage_key"].endswith("logo.png")

    # The artwork exists in 'uploading' state
    arts = client.get(f"/api/v1/projects/{pid}/artworks", headers=headers).json()["data"]
    assert len(arts) == 1
    assert arts[0]["status"] == "uploading"
    assert arts[0]["kind"] == "original"


@pytest.mark.usefixtures("require_db")
def test_other_users_project_is_hidden():
    headers_a = _auth_headers()
    pid = client.post(
        "/api/v1/projects", json={"name": "A"}, headers=headers_a
    ).json()["data"]["id"]

    headers_b = _auth_headers()
    # User B cannot see or reach user A's project (404, not 403 — no existence leak)
    assert client.get(f"/api/v1/projects/{pid}", headers=headers_b).status_code == 404


@pytest.mark.usefixtures("require_db", "require_storage")
def test_full_upload_and_confirm():
    headers = _auth_headers()
    pid = client.post(
        "/api/v1/projects", json={"name": "Upload"}, headers=headers
    ).json()["data"]["id"]

    up = client.post(
        f"/api/v1/projects/{pid}/artworks/upload-url",
        json={"filename": "logo.png", "content_type": "image/png", "size_bytes": len(_PNG)},
        headers=headers,
    ).json()["data"]
    aid = up["artwork_id"]

    # Upload the bytes straight to storage via the presigned URL.
    put = httpx.put(up["upload_url"], content=_PNG, headers={"Content-Type": "image/png"})
    assert put.status_code in (200, 204), put.text

    # Confirm -> artwork becomes ready with recorded size
    confirmed = client.post(
        f"/api/v1/projects/{pid}/artworks/{aid}/confirm",
        json={"width": 1, "height": 1},
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()["data"]
    assert body["status"] == "ready"
    assert body["size_bytes"] == len(_PNG)

    # Get returns a working presigned download URL
    detail = client.get(
        f"/api/v1/projects/{pid}/artworks/{aid}", headers=headers
    ).json()["data"]
    assert detail["download_url"]
    got = httpx.get(detail["download_url"])
    assert got.status_code == 200
    assert got.content == _PNG


@pytest.mark.usefixtures("require_db")
def test_confirm_without_upload_conflicts():
    headers = _auth_headers()
    pid = client.post(
        "/api/v1/projects", json={"name": "NoUpload"}, headers=headers
    ).json()["data"]["id"]
    aid = client.post(
        f"/api/v1/projects/{pid}/artworks/upload-url",
        json={"filename": "logo.png", "content_type": "image/png"},
        headers=headers,
    ).json()["data"]["artwork_id"]

    # Confirming before uploading -> 409 if storage is up, 503 if it's unreachable.
    resp = client.post(
        f"/api/v1/projects/{pid}/artworks/{aid}/confirm", json={}, headers=headers
    )
    assert resp.status_code in (409, 503)
