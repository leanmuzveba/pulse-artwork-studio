"""Integration tests for the auth flow (require a PostgreSQL database).

Skipped automatically when no DB is reachable — see tests/conftest.py.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

pytestmark = pytest.mark.usefixtures("require_db")


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def test_register_login_me_flow():
    email = _unique_email()
    password = "sup3r-secret-pw"

    # Register
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["data"]["email"] == email
    assert body["data"]["is_verified"] is False

    # Duplicate registration is a conflict
    r_dup = client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert r_dup.status_code == 409
    assert r_dup.json()["error"]["code"] == "conflict"

    # Login
    r_login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert r_login.status_code == 200, r_login.text
    tokens = r_login.json()["data"]
    assert tokens["token_type"] == "bearer"
    access, refresh = tokens["access_token"], tokens["refresh_token"]

    # Wrong password is rejected
    r_bad = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "nope"}
    )
    assert r_bad.status_code == 401

    # /users/me requires the access token
    assert client.get("/api/v1/users/me").status_code == 401
    r_me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
    assert r_me.status_code == 200, r_me.text
    assert r_me.json()["data"]["email"] == email

    # Refresh yields a usable new access token
    r_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r_refresh.status_code == 200, r_refresh.text
    new_access = r_refresh.json()["data"]["access_token"]
    r_me2 = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {new_access}"}
    )
    assert r_me2.status_code == 200

    # A refresh token cannot be used as an access token
    r_wrong = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert r_wrong.status_code == 401
