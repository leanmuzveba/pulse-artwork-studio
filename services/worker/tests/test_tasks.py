"""Unit tests for system tasks (run the task bodies directly, no broker needed)."""

from __future__ import annotations

from worker.tasks.system import echo, ping


def test_ping_returns_pong():
    assert ping.run() == "pong"


def test_echo_roundtrips_payload():
    assert echo.run({"artwork_id": "abc"}) == {"echo": {"artwork_id": "abc"}}
