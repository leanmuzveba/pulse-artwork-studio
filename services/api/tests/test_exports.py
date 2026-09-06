"""Integration tests for the export pipeline.

The Celery layer (`app.services.queue`) is monkeypatched, so these need no
broker/worker — they verify the API's export creation, authorization, and the
reconcile-on-poll logic. DB is always required; the success/failure flows also
need object storage (to produce a 'ready' artwork via the real upload+confirm).
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

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


def _new_project(headers) -> str:
    return client.post(
        "/api/v1/projects", json={"name": "Exports"}, headers=headers
    ).json()["data"]["id"]


def _uploaded_artwork(headers, pid) -> str:
    """Create an artwork and upload it (needs storage)."""
    up = client.post(
        f"/api/v1/projects/{pid}/artworks/upload-url",
        json={"filename": "logo.png", "content_type": "image/png", "size_bytes": len(_PNG)},
        headers=headers,
    ).json()["data"]
    httpx.put(up["upload_url"], content=_PNG, headers={"Content-Type": "image/png"})
    client.post(
        f"/api/v1/projects/{pid}/artworks/{up['artwork_id']}/confirm",
        json={},
        headers=headers,
    )
    return up["artwork_id"]


@pytest.mark.usefixtures("require_db")
def test_create_export_requires_auth():
    body = {
        "project_id": str(uuid.uuid4()),
        "artwork_id": str(uuid.uuid4()),
        "format": "png",
    }
    assert client.post("/api/v1/exports", json=body).status_code == 401


@pytest.mark.usefixtures("require_db")
def test_export_on_unready_artwork_conflicts():
    headers = _auth_headers()
    pid = _new_project(headers)
    # upload-url creates an 'uploading' (not ready) artwork
    aid = client.post(
        f"/api/v1/projects/{pid}/artworks/upload-url",
        json={"filename": "logo.png", "content_type": "image/png"},
        headers=headers,
    ).json()["data"]["artwork_id"]

    resp = client.post(
        "/api/v1/exports",
        json={"project_id": pid, "artwork_id": aid, "format": "png"},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.usefixtures("require_db", "require_storage")
def test_png_export_success_flow(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_export", lambda *a, **k: "fake-export-task-1")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    created = client.post(
        "/api/v1/exports",
        json={"project_id": pid, "artwork_id": aid, "format": "png"},
        headers=headers,
    )
    assert created.status_code == 202, created.text
    export = created.json()["data"]
    assert export["status"] == "pending"
    export_id = export["id"]

    monkeypatch.setattr(
        queue,
        "get_job_state",
        lambda task_id: (
            "SUCCESS",
            {
                "bucket": "pulse-exports",
                "key": f"projects/{pid}/exports/{export_id}.png",
                "mime_type": "image/png",
                "size_bytes": 123,
                "width": 1,
                "height": 1,
                "dpi": 300,
            },
        ),
    )
    polled = client.get(f"/api/v1/exports/{export_id}", headers=headers).json()["data"]
    assert polled["status"] == "ready"
    assert polled["width"] == 1 and polled["height"] == 1 and polled["dpi"] == 300
    assert polled["download_url"]


@pytest.mark.usefixtures("require_db", "require_storage")
def test_svg_export_success_has_no_pixel_dimensions(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_export", lambda *a, **k: "fake-export-task-svg")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    created = client.post(
        "/api/v1/exports",
        json={"project_id": pid, "artwork_id": aid, "format": "svg"},
        headers=headers,
    )
    assert created.status_code == 202, created.text
    export_id = created.json()["data"]["id"]

    monkeypatch.setattr(
        queue,
        "get_job_state",
        lambda task_id: (
            "SUCCESS",
            {
                "bucket": "pulse-exports",
                "key": f"projects/{pid}/exports/{export_id}.svg",
                "mime_type": "image/svg+xml",
                "size_bytes": 456,
                "width": None,
                "height": None,
                "dpi": None,
            },
        ),
    )
    polled = client.get(f"/api/v1/exports/{export_id}", headers=headers).json()["data"]
    assert polled["status"] == "ready"
    assert polled["width"] is None and polled["dpi"] is None
    assert polled["download_url"]


@pytest.mark.usefixtures("require_db", "require_storage")
@pytest.mark.parametrize("export_format", ["png", "pdf", "svg"])
def test_supported_formats_are_accepted(monkeypatch, export_format):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_export", lambda *a, **k: "fake-export-task")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    resp = client.post(
        "/api/v1/exports",
        json={"project_id": pid, "artwork_id": aid, "format": export_format},
        headers=headers,
    )
    assert resp.status_code == 202, resp.text


@pytest.mark.usefixtures("require_db", "require_storage")
def test_export_failure_flow(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_export", lambda *a, **k: "fake-export-task-2")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    export_id = client.post(
        "/api/v1/exports",
        json={"project_id": pid, "artwork_id": aid, "format": "png"},
        headers=headers,
    ).json()["data"]["id"]

    monkeypatch.setattr(
        queue, "get_job_state", lambda task_id: ("FAILURE", ValueError("boom"))
    )
    polled = client.get(f"/api/v1/exports/{export_id}", headers=headers).json()["data"]
    assert polled["status"] == "failed"
    assert "boom" in polled["error_message"]
