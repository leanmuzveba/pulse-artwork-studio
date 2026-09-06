"""Exports — produce PNG/SVG/PDF outputs of an artwork.

Lifecycle: PENDING -> READY | FAILED

The worker returns its result via Celery's result backend; this router
reconciles that state into the exports row whenever the client polls.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, load_owned_artwork, load_owned_project
from app.core.config import get_settings
from app.core.errors import APIError, ErrorCode
from app.core.logging import request_id_ctx
from app.db.enums import ArtworkStatus, ExportStatus
from app.db.models import Export, User
from app.db.session import get_session
from app.schemas.common import SuccessResponse
from app.schemas.exports import ExportCreateRequest, ExportDetailResponse, ExportResponse
from app.services import queue, storage

router = APIRouter()
settings = get_settings()

_TERMINAL = {ExportStatus.READY, ExportStatus.FAILED}


@router.post(
    "",
    response_model=SuccessResponse[ExportResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create an export (async)",
)
async def create_export(
    payload: ExportCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ExportResponse]:
    artwork = await load_owned_artwork(
        session, user, payload.project_id, payload.artwork_id
    )
    if artwork.status != ArtworkStatus.READY:
        raise APIError(
            ErrorCode.CONFLICT,
            "Artwork is not ready. Confirm the upload before exporting.",
            status_code=409,
        )
    if not artwork.storage_bucket or not artwork.storage_key:
        raise APIError(
            ErrorCode.CONFLICT, "Artwork has no stored file.", status_code=409
        )

    export = Export(
        project_id=payload.project_id,
        artwork_id=payload.artwork_id,
        format=payload.format,
        status=ExportStatus.PENDING,
    )
    session.add(export)
    await session.flush()  # assign export.id
    export.task_id = queue.enqueue_export(
        export.id,
        payload.format.value,
        artwork.storage_bucket,
        artwork.storage_key,
        payload.parameters,
        payload.project_id,
    )
    await session.commit()
    await session.refresh(export)
    return SuccessResponse(
        data=ExportResponse.model_validate(export), request_id=request_id_ctx.get()
    )


@router.get(
    "/{export_id}",
    response_model=SuccessResponse[ExportDetailResponse],
    summary="Get an export's status, with a signed download URL once ready",
)
async def get_export(
    export_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ExportDetailResponse]:
    export = await session.get(Export, export_id)
    if export is None:
        raise APIError(ErrorCode.NOT_FOUND, "Export not found.", status_code=404)
    await load_owned_project(session, user, export.project_id)  # authorize

    await _reconcile(export, session)
    data = ExportDetailResponse.model_validate(export)
    if export.status == ExportStatus.READY and export.storage_key:
        data.download_url = storage.create_presigned_download(
            export.storage_bucket, export.storage_key, settings.s3_signed_url_ttl_seconds
        )
    return SuccessResponse(data=data, request_id=request_id_ctx.get())


async def _reconcile(export: Export, session: AsyncSession) -> None:
    """Fold the worker's Celery state into the export row. Best-effort; never raises."""
    if export.status in _TERMINAL or not export.task_id:
        return
    try:
        state, result = queue.get_job_state(export.task_id)
    except Exception:
        return  # broker unreachable — leave the row unchanged

    if state == "SUCCESS" and isinstance(result, dict):
        export.status = ExportStatus.READY
        export.storage_bucket = result.get("bucket")
        export.storage_key = result.get("key")
        export.width = result.get("width")
        export.height = result.get("height")
        export.dpi = result.get("dpi")
    elif state == "FAILURE":
        export.status = ExportStatus.FAILED
        export.error_message = str(result)[:1000]
    else:
        return

    await session.commit()
    await session.refresh(export)
