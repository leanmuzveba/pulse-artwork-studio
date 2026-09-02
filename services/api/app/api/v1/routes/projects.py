"""Projects — CRUD over a user's artwork projects (Phase 1, next step)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes._stub import not_implemented

router = APIRouter()


@router.get("", summary="List the current user's projects")
async def list_projects() -> None:
    raise not_implemented("Listing projects")


@router.post("", summary="Create a project")
async def create_project() -> None:
    raise not_implemented("Creating a project")


@router.get("/{project_id}", summary="Get a project")
async def get_project(project_id: str) -> None:
    raise not_implemented("Fetching a project")
