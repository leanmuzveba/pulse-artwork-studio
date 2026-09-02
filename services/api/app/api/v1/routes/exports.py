"""Exports — produce PNG/SVG/PDF outputs (Phase 4; stub for now)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes._stub import not_implemented

router = APIRouter()


@router.post("", summary="Create an export")
async def create_export() -> None:
    raise not_implemented("Exports")
