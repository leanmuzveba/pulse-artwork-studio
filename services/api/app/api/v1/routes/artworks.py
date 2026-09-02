"""Artworks — upload orchestration and artwork metadata (Phase 1, next step).

Nested under a project: /projects/{project_id}/artworks
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes._stub import not_implemented

router = APIRouter()


@router.post("/{project_id}/artworks/upload-url", summary="Request a signed upload URL")
async def create_upload_url(project_id: str) -> None:
    raise not_implemented("Signed upload URLs")


@router.post("/{project_id}/artworks", summary="Confirm an uploaded artwork's metadata")
async def confirm_artwork(project_id: str) -> None:
    raise not_implemented("Artwork metadata confirmation")


@router.get("/{project_id}/artworks", summary="List a project's artworks")
async def list_artworks(project_id: str) -> None:
    raise not_implemented("Listing artworks")
