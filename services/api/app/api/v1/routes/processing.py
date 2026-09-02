"""Processing jobs — enqueue async work and poll status (Phase 1, next step).

Job lifecycle: REQUESTED -> QUEUED -> PROCESSING -> COMPLETED | FAILED
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes._stub import not_implemented

router = APIRouter()


@router.post("/jobs", summary="Create a processing job")
async def create_job() -> None:
    raise not_implemented("Creating processing jobs")


@router.get("/jobs/{job_id}", summary="Get a processing job's status")
async def get_job(job_id: str) -> None:
    raise not_implemented("Fetching job status")
