"""Processing jobs — enqueue async work and poll status.

Lifecycle: REQUESTED -> QUEUED -> PROCESSING -> COMPLETED | FAILED

The worker returns its result via Celery's result backend; this router
reconciles that state into the processing_jobs row whenever the client polls.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, load_owned_artwork, load_owned_project
from app.core.errors import APIError, ErrorCode
from app.core.logging import request_id_ctx
from app.db.enums import ArtworkKind, ArtworkStatus, JobOperation, JobStatus
from app.db.models import Artwork, ProcessingJob, User
from app.db.session import get_session
from app.schemas.common import SuccessResponse
from app.schemas.processing import JobCreateRequest, JobResponse
from app.services import queue

router = APIRouter()

# All processing operations are now implemented (Phase 3 complete; crop/
# rotate/flip/resize — the Phase 3 "editor canvas tools" — added after).
SUPPORTED_OPERATIONS = {
    JobOperation.METADATA,
    JobOperation.ENHANCE,
    JobOperation.UPSCALE,
    JobOperation.BACKGROUND_REMOVAL,
    JobOperation.HALFTONE,
    JobOperation.EMBROIDERY,
    JobOperation.VECTORIZE,
    JobOperation.DTF_CHECK,
    JobOperation.CROP,
    JobOperation.ROTATE,
    JobOperation.FLIP,
    JobOperation.RESIZE,
}

# Operations that produce a new derived Artwork rather than annotating the original.
_DERIVING_OPERATIONS = {
    JobOperation.ENHANCE,
    JobOperation.UPSCALE,
    JobOperation.BACKGROUND_REMOVAL,
    JobOperation.HALFTONE,
    JobOperation.EMBROIDERY,
    JobOperation.VECTORIZE,
    JobOperation.CROP,
    JobOperation.ROTATE,
    JobOperation.FLIP,
    JobOperation.RESIZE,
}
_TERMINAL = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}


@router.post(
    "/jobs",
    response_model=SuccessResponse[JobResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a processing job (async)",
)
async def create_job(
    payload: JobCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[JobResponse]:
    if payload.operation not in SUPPORTED_OPERATIONS:
        raise APIError(
            ErrorCode.VALIDATION_ERROR,
            f"Operation '{payload.operation.value}' is not available yet.",
            status_code=422,
        )

    artwork = await load_owned_artwork(
        session, user, payload.project_id, payload.artwork_id
    )
    if artwork.status != ArtworkStatus.READY:
        raise APIError(
            ErrorCode.CONFLICT,
            "Artwork is not ready. Confirm the upload before processing.",
            status_code=409,
        )
    if not artwork.storage_bucket or not artwork.storage_key:
        raise APIError(
            ErrorCode.CONFLICT, "Artwork has no stored file.", status_code=409
        )

    job = ProcessingJob(
        project_id=payload.project_id,
        artwork_id=payload.artwork_id,
        operation=payload.operation,
        parameters=payload.parameters,
        status=JobStatus.QUEUED,
    )
    session.add(job)
    await session.flush()  # assign job.id
    job.task_id = queue.enqueue_job(
        payload.operation.value,
        job.id,
        artwork.storage_bucket,
        artwork.storage_key,
        payload.parameters,
        payload.project_id,
    )
    await session.commit()
    await session.refresh(job)
    return SuccessResponse(
        data=JobResponse.model_validate(job), request_id=request_id_ctx.get()
    )


@router.get(
    "/jobs/{job_id}",
    response_model=SuccessResponse[JobResponse],
    summary="Get a processing job's status",
)
async def get_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[JobResponse]:
    job = await session.get(ProcessingJob, job_id)
    if job is None:
        raise APIError(ErrorCode.NOT_FOUND, "Job not found.", status_code=404)
    await load_owned_project(session, user, job.project_id)  # authorize

    await _reconcile(job, session)
    return SuccessResponse(
        data=JobResponse.model_validate(job), request_id=request_id_ctx.get()
    )


async def _reconcile(job: ProcessingJob, session: AsyncSession) -> None:
    """Fold the worker's Celery state into the job row. Best-effort; never raises."""
    if job.status in _TERMINAL or not job.task_id:
        return
    try:
        state, result = queue.get_job_state(job.task_id)
    except Exception:
        return  # broker unreachable — leave the row unchanged

    now = datetime.now(UTC)
    changed = False

    if state == "STARTED" and job.status != JobStatus.PROCESSING:
        job.status = JobStatus.PROCESSING
        job.started_at = job.started_at or now
        changed = True
    elif state == "SUCCESS":
        await _apply_success(job, result, session, now)
        changed = True
    elif state == "FAILURE":
        job.status = JobStatus.FAILED
        job.error_code = "processing_error"
        job.error_message = str(result)[:1000]
        job.started_at = job.started_at or now
        job.finished_at = now
        changed = True

    if changed:
        await session.commit()
        await session.refresh(job)


async def _apply_success(
    job: ProcessingJob, result: Any, session: AsyncSession, now: datetime
) -> None:
    # For metadata, enrich the (immutable-file) original artwork's metadata.
    if job.operation == JobOperation.METADATA and isinstance(result, dict):
        artwork = await session.get(Artwork, job.artwork_id)
        if artwork is not None:
            if result.get("width") is not None:
                artwork.width = result["width"]
            if result.get("height") is not None:
                artwork.height = result["height"]
            if result.get("source_dpi") is not None:
                artwork.source_dpi = result["source_dpi"]
        job.result_artwork_id = job.artwork_id
    elif job.operation == JobOperation.DTF_CHECK and isinstance(result, dict):
        # Analysis only — the report is the result, no image is produced.
        job.result_data = result
        job.result_artwork_id = job.artwork_id
    elif job.operation in _DERIVING_OPERATIONS and isinstance(result, dict):
        # The original is immutable — the op's output becomes a new derived Artwork.
        parent = await session.get(Artwork, job.artwork_id)
        derived = Artwork(
            project_id=job.project_id,
            parent_artwork_id=job.artwork_id,
            kind=ArtworkKind.DERIVED,
            status=ArtworkStatus.READY,
            original_filename=parent.original_filename if parent else None,
            mime_type=result.get("mime_type"),
            size_bytes=result.get("size_bytes"),
            width=result.get("width"),
            height=result.get("height"),
            storage_bucket=result.get("bucket"),
            storage_key=result.get("key"),
        )
        session.add(derived)
        await session.flush()
        job.result_artwork_id = derived.id

    job.status = JobStatus.COMPLETED
    job.progress = 100
    job.started_at = job.started_at or now
    job.finished_at = now
