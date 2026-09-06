"""Smoke tests for the app skeleton: health, envelopes, request id, OpenAPI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_liveness_readiness_alias():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "pulse-api"


def test_readiness_reports_dependency_checks():
    # Without a database the endpoint reports "degraded" (503); with one, "ok" (200).
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "database" in body["checks"]
    assert body["status"] in ("ok", "degraded")


def test_request_id_header_present():
    resp = client.get("/api/v1/health")
    assert resp.headers.get("X-Request-ID")


def test_not_implemented_uses_error_envelope():
    # /subscriptions/entitlements is still a stub; asserts the 501 envelope shape.
    resp = client.get("/api/v1/subscriptions/entitlements")
    assert resp.status_code == 501
    body = resp.json()
    assert body["error"]["code"] == "not_implemented"
    assert "request_id" in body


def test_unknown_route_is_structured_404():
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_openapi_is_served():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"] == "Pulse Artwork Studio AI"
