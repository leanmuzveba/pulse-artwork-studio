"""Aggregate router for API v1.

Service boundaries mirror the Technical Design: Auth, Projects, Artworks,
Processing, Exports, Subscriptions/Entitlements, Users. Only health is
implemented in this Phase-1 step; the rest are registered as stubs so the route
surface and OpenAPI document exist from day one.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    artworks,
    auth,
    exports,
    health,
    processing,
    projects,
    subscriptions,
    users,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, prefix="/health", tags=["health"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_v1_router.include_router(artworks.router, prefix="/projects", tags=["artworks"])
api_v1_router.include_router(processing.router, prefix="/processing", tags=["processing"])
api_v1_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_v1_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
