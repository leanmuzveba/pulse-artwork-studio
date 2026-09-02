"""Health / readiness endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import __version__
from app.core.config import get_settings
from app.core.logging import request_id_ctx
from app.schemas.common import HealthStatus

router = APIRouter()
settings = get_settings()


@router.get("", response_model=HealthStatus, summary="Liveness")
async def health() -> HealthStatus:
    """Report that the API process is up (no dependency checks)."""
    return HealthStatus(
        status="ok",
        service="pulse-api",
        version=__version__,
        environment=settings.environment,
    )


@router.get("/ready", summary="Readiness (checks dependencies)")
async def ready() -> JSONResponse:
    """Check dependencies and return 200 when ready, 503 when degraded.

    Currently checks PostgreSQL; Redis and object storage are added as they are
    wired in. Imported lazily so liveness and unit tests stay driver-free.
    """
    from app.db.session import check_database

    try:
        db_ok = await asyncio.wait_for(check_database(), timeout=3.0)
    except (TimeoutError, asyncio.TimeoutError):
        db_ok = False

    checks = {"database": "ok" if db_ok else "unavailable"}
    body = {
        "status": "ok" if db_ok else "degraded",
        "checks": checks,
        "request_id": request_id_ctx.get(),
    }
    return JSONResponse(status_code=200 if db_ok else 503, content=body)
