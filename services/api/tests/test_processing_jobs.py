"""Integration tests for the processing-job pipeline.

The Celery layer (`app.services.queue`) is monkeypatched, so these need no
broker/worker — they verify the API's job creation, authorization, and the
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
        "/api/v1/projects", json={"name": "Jobs"}, headers=headers
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
def test_create_job_requires_auth():
    body = {
        "project_id": str(uuid.uuid4()),
        "artwork_id": str(uuid.uuid4()),
        "operation": "metadata",
    }
    assert client.post("/api/v1/processing/jobs", json=body).status_code == 401


@pytest.mark.usefixtures("require_db")
def test_unsupported_operation_is_rejected():
    headers = _auth_headers()
    body = {
        "project_id": str(uuid.uuid4()),
        "artwork_id": str(uuid.uuid4()),
        "operation": "vectorize",  # valid enum, not yet supported
    }
    resp = client.post("/api/v1/processing/jobs", json=body, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


@pytest.mark.usefixtures("require_db")
def test_job_on_unready_artwork_conflicts():
    headers = _auth_headers()
    pid = _new_project(headers)
    # upload-url creates an 'uploading' (not ready) artwork
    aid = client.post(
        f"/api/v1/projects/{pid}/artworks/upload-url",
        json={"filename": "logo.png", "content_type": "image/png"},
        headers=headers,
    ).json()["data"]["artwork_id"]

    resp = client.post(
        "/api/v1/processing/jobs",
        json={"project_id": pid, "artwork_id": aid, "operation": "metadata"},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.usefixtures("require_db", "require_storage")
def test_metadata_job_success_flow(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_job", lambda *a, **k: "fake-task-1")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    created = client.post(
        "/api/v1/processing/jobs",
        json={"project_id": pid, "artwork_id": aid, "operation": "metadata"},
        headers=headers,
    )
    assert created.status_code == 202, created.text
    job = created.json()["data"]
    assert job["status"] == "queued"
    job_id = job["id"]

    # Worker reports success with extracted metadata.
    monkeypatch.setattr(
        queue,
        "get_job_state",
        lambda task_id: ("SUCCESS", {"width": 1, "height": 1, "source_dpi": 300}),
    )
    polled = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers).json()["data"]
    assert polled["status"] == "completed"
    assert polled["progress"] == 100
    assert polled["result_artwork_id"] == aid
    assert polled["finished_at"] is not None

    # The original artwork's metadata was enriched.
    art = client.get(
        f"/api/v1/projects/{pid}/artworks/{aid}", headers=headers
    ).json()["data"]
    assert art["width"] == 1 and art["height"] == 1 and art["source_dpi"] == 300


@pytest.mark.usefixtures("require_db", "require_storage")
def test_upscale_job_success_creates_derived_artwork(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_job", lambda *a, **k: "fake-task-upscale")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    created = client.post(
        "/api/v1/processing/jobs",
        json={"project_id": pid, "artwork_id": aid, "operation": "upscale"},
        headers=headers,
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["data"]["id"]

    monkeypatch.setattr(
        queue,
        "get_job_state",
        lambda task_id: (
            "SUCCESS",
            {
                "width": 2,
                "height": 2,
                "format": "PNG",
                "mode": "RGBA",
                "has_alpha": True,
                "source_dpi": None,
                "bucket": "pulse-derived",
                "key": f"projects/{pid}/derived/{job_id}/upscale.png",
                "mime_type": "image/png",
                "size_bytes": 123,
            },
        ),
    )
    polled = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers).json()["data"]
    assert polled["status"] == "completed"
    result_id = polled["result_artwork_id"]
    assert result_id != aid  # a new derived artwork, not the original

    derived = client.get(
        f"/api/v1/projects/{pid}/artworks/{result_id}", headers=headers
    ).json()["data"]
    assert derived["width"] == 2 and derived["height"] == 2
    assert derived["kind"] == "derived"

    # The original is untouched (immutable).
    original = client.get(
        f"/api/v1/projects/{pid}/artworks/{aid}", headers=headers
    ).json()["data"]
    assert original["kind"] == "original"
    assert original["width"] != 2


@pytest.mark.usefixtures("require_db", "require_storage")
def test_dtf_check_job_success_stores_report_without_derived_artwork(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_job", lambda *a, **k: "fake-task-dtf")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    created = client.post(
        "/api/v1/processing/jobs",
        json={"project_id": pid, "artwork_id": aid, "operation": "dtf_check"},
        headers=headers,
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["data"]["id"]

    report = {
        "width": 1,
        "height": 1,
        "format": "PNG",
        "mode": "RGBA",
        "has_alpha": True,
        "source_dpi": None,
        "effective_dpi": None,
        "checks": [
            {"code": "image_too_small", "severity": "error", "message": "too small"}
        ],
        "ready": False,
    }
    monkeypatch.setattr(queue, "get_job_state", lambda task_id: ("SUCCESS", report))

    polled = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers).json()["data"]
    assert polled["status"] == "completed"
    assert polled["result_data"] == report
    assert polled["result_artwork_id"] == aid  # inspects the original, no new artwork


@pytest.mark.usefixtures("require_db", "require_storage")
@pytest.mark.parametrize(
    "operation", ["metadata", "enhance", "upscale", "background_removal", "dtf_check"]
)
def test_supported_operations_are_accepted(monkeypatch, operation):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_job", lambda *a, **k: "fake-task")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    resp = client.post(
        "/api/v1/processing/jobs",
        json={"project_id": pid, "artwork_id": aid, "operation": operation},
        headers=headers,
    )
    assert resp.status_code == 202, resp.text


@pytest.mark.usefixtures("require_db", "require_storage")
def test_metadata_job_failure_flow(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_job", lambda *a, **k: "fake-task-2")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    job_id = client.post(
        "/api/v1/processing/jobs",
        json={"project_id": pid, "artwork_id": aid, "operation": "metadata"},
        headers=headers,
    ).json()["data"]["id"]

    monkeypatch.setattr(
        queue, "get_job_state", lambda task_id: ("FAILURE", ValueError("boom"))
    )
    polled = client.get(f"/api/v1/processing/jobs/{job_id}", headers=headers).json()["data"]
    assert polled["status"] == "failed"
    assert polled["error_code"] == "processing_error"
    assert "boom" in polled["error_message"]
