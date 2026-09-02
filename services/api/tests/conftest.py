"""Shared pytest fixtures.

Integration tests that need a real PostgreSQL are skipped automatically when no
database is reachable (e.g. local runs without Docker); they run in CI where a
Postgres service is available and migrations have been applied.
"""

from __future__ import annotations

import asyncio

import pytest

from app.db.session import check_database


@pytest.fixture(scope="session")
def db_available() -> bool:
    try:
        return asyncio.run(check_database())
    except Exception:
        return False


@pytest.fixture
def require_db(db_available: bool) -> None:
    if not db_available:
        pytest.skip("no database available (integration test)")
