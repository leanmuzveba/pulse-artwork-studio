"""Subscriptions / entitlements — plans and usage limits (Phase 5; stub for now).

Entitlements are modelled from Phase 1 even though billing activates later.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes._stub import not_implemented

router = APIRouter()


@router.get("/entitlements", summary="Get the current user's entitlements")
async def get_entitlements() -> None:
    raise not_implemented("Entitlements")
