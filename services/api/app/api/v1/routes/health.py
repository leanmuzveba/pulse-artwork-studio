"""Health / readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.schemas.common import HealthStatus

router = APIRouter()
settings = get_settings()


@router.get("", response_model=HealthStatus, summary="Service readiness")
async def health() -> HealthStatus:
    """Report that the API is up.

    Dependency checks (PostgreSQL, Redis, object storage) are added when those
    services are wired in the next Phase-1 step.
    """
    return HealthStatus(
        status="ok",
        service="pulse-api",
        version=__version__,
        environment=settings.environment,
    )
