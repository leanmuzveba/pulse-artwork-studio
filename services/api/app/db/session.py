"""Async engine, session factory, and a readiness check.

The engine is created lazily on first use so importing this module never opens a
connection (keeps unit tests and app import DB-free until something asks).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_engine_loop: asyncio.AbstractEventLoop | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process's async engine, recreating it if the running event
    loop has changed since it was built.

    asyncpg connections (and the pool holding them) are bound to the event
    loop active when they're created. A single module-level engine is
    correct in production (uvicorn runs one loop for the process's life),
    but in tests it's routinely wrong: pytest-asyncio and Starlette's
    TestClient can each spin up their own loop per test/request, and a
    stale engine bound to an already-closed loop fails with "attached to a
    different loop" / "Event loop is closed". Rebuilding on loop change
    fixes both cases with no test-side workarounds needed.
    """
    global _engine, _engine_loop, _sessionmaker
    loop = asyncio.get_running_loop()
    if _engine is None or _engine_loop is not loop:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
        )
        _engine_loop = loop
        _sessionmaker = None  # bound to the old engine; must be rebuilt too
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    engine = get_engine()  # may reset _sessionmaker if the loop changed
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session."""
    async with get_sessionmaker()() as session:
        yield session


async def check_database() -> bool:
    """Return True if a trivial query succeeds. Never raises."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
