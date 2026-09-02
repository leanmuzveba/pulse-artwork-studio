"""Users — profile and account (Phase 1, next step)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes._stub import not_implemented

router = APIRouter()


@router.get("/me", summary="Get the authenticated user's profile")
async def get_me() -> None:
    raise not_implemented("User profile")
