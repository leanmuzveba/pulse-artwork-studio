"""Integration tests for the gang sheet pipeline.

The Celery layer (`app.services.queue`) is monkeypatched, so these need no
broker/worker — they verify the API's gang-sheet creation, authorization, the
mm<->px conversion, and the reconcile-on-poll logic. DB is always required;
the success/failure flows also need object storage (to produce a 'ready'
artwork via the real upload+confirm).
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
        "/api/v1/projects", json={"name": "Gang Sheets"}, headers=headers
    ).json()["data"]["id"]


def _uploaded_artwork(headers, pid) -> str:
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
def test_create_gang_sheet_requires_auth():
    body = {
        "project_id": str(uuid.uuid4()),
        "sheet_width_mm": 300,
        "items": [{"artwork_id": str(uuid.uuid4())}],
    }
    assert client.post("/api/v1/gang-sheets", json=body).status_code == 401


@pytest.mark.usefixtures("require_db", "require_storage")
def test_gang_sheet_with_unready_artwork_conflicts():
    headers = _auth_headers()
    pid = _new_project(headers)
    aid = client.post(
        f"/api/v1/projects/{pid}/artworks/upload-url",
        json={"filename": "logo.png", "content_type": "image/png"},
        headers=headers,
    ).json()["data"]["artwork_id"]

    resp = client.post(
        "/api/v1/gang-sheets",
        json={
            "project_id": pid,
            "sheet_width_mm": 300,
            "items": [{"artwork_id": aid}],
        },
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.usefixtures("require_db")
def test_too_many_total_copies_is_rejected():
    headers = _auth_headers()
    pid = _new_project(headers)
    resp = client.post(
        "/api/v1/gang-sheets",
        json={
            "project_id": pid,
            "sheet_width_mm": 300,
            "items": [{"artwork_id": str(uuid.uuid4()), "copies": 301}],
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.usefixtures("require_db", "require_storage")
def test_gang_sheet_success_flow_converts_px_placements_to_mm(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_gang_sheet", lambda *a, **k: "fake-gs-task-1")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    created = client.post(
        "/api/v1/gang-sheets",
        json={
            "project_id": pid,
            "sheet_width_mm": 300,
            "spacing_mm": 5,
            "dpi": 300,
            "items": [{"artwork_id": aid, "copies": 2, "rotate_deg": 90}],
        },
        headers=headers,
    )
    assert created.status_code == 202, created.text
    gs = created.json()["data"]
    assert gs["status"] == "pending"
    assert gs["items"] == [{"artwork_id": aid, "copies": 2, "rotate_deg": 90}]
    gang_sheet_id = gs["id"]

    # 300 DPI: 1mm ~= 11.81px: worker reports px, API should convert back to mm.
    monkeypatch.setattr(
        queue,
        "get_job_state",
        lambda task_id: (
            "SUCCESS",
            {
                "bucket": "pulse-exports",
                "key": f"projects/{pid}/gang-sheets/{gang_sheet_id}.png",
                "mime_type": "image/png",
                "size_bytes": 999,
                "sheet_width_px": 3543,  # ~300mm
                "sheet_height_px": 1181,  # ~100mm
                "dpi": 300,
                "placements": [
                    {
                        "artwork_id": aid,
                        "x": 59,  # ~5mm
                        "y": 59,
                        "width": 236,  # ~20mm
                        "height": 236,
                        "rotate_deg": 90,
                    }
                ],
            },
        ),
    )
    polled = client.get(f"/api/v1/gang-sheets/{gang_sheet_id}", headers=headers).json()["data"]
    assert polled["status"] == "ready"
    assert polled["sheet_height_mm"] == 100
    assert polled["layout"] == [
        {"artwork_id": aid, "x": 5, "y": 5, "width": 20, "height": 20, "rotate_deg": 90}
    ]
    assert polled["download_url"]


@pytest.mark.usefixtures("require_db", "require_storage")
def test_gang_sheet_failure_flow(monkeypatch):
    from app.services import queue

    monkeypatch.setattr(queue, "enqueue_gang_sheet", lambda *a, **k: "fake-gs-task-2")

    headers = _auth_headers()
    pid = _new_project(headers)
    aid = _uploaded_artwork(headers, pid)

    gang_sheet_id = client.post(
        "/api/v1/gang-sheets",
        json={"project_id": pid, "sheet_width_mm": 300, "items": [{"artwork_id": aid}]},
        headers=headers,
    ).json()["data"]["id"]

    monkeypatch.setattr(
        queue, "get_job_state", lambda task_id: ("FAILURE", ValueError("boom"))
    )
    polled = client.get(f"/api/v1/gang-sheets/{gang_sheet_id}", headers=headers).json()["data"]
    assert polled["status"] == "failed"
    assert "boom" in polled["error_message"]
