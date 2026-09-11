"""Gang sheets — auto-nest several artworks onto one DTF print sheet.

Lifecycle: PENDING -> READY | FAILED (mirrors exports.py). Sheet dimensions
and spacing are tracked in millimeters (the print-shop unit); the worker
works in pixels, so this router converts at the configured DPI in both
directions — on enqueue (mm -> px) and on reconciling a successful result
(px -> mm, for `sheet_height_mm` and each placement in `layout`).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, load_owned_artwork, load_owned_project
from app.core.config import get_settings
from app.core.errors import APIError, ErrorCode
from app.core.logging import request_id_ctx
from app.db.enums import ArtworkStatus, GangSheetStatus
from app.db.models import GangSheet, User
from app.db.session import get_session
from app.schemas.common import SuccessResponse
from app.schemas.gang_sheet import (
    GangSheetCreateRequest,
    GangSheetDetailResponse,
    GangSheetResponse,
)
from app.services import queue, storage

router = APIRouter()
settings = get_settings()

_MM_PER_INCH = 25.4
_TERMINAL = {GangSheetStatus.READY, GangSheetStatus.FAILED}


def _mm_to_px(mm: int, dpi: int) -> int:
    return max(1, round(mm / _MM_PER_INCH * dpi))


def _px_to_mm(px: int, dpi: int) -> int:
    return round(px / dpi * _MM_PER_INCH)


@router.post(
    "",
    response_model=SuccessResponse[GangSheetResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a gang sheet (async)",
)
async def create_gang_sheet(
    payload: GangSheetCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[GangSheetResponse]:
    await load_owned_project(session, user, payload.project_id)

    worker_items = []
    for item in payload.items:
        artwork = await load_owned_artwork(
            session, user, payload.project_id, item.artwork_id
        )
        if artwork.status != ArtworkStatus.READY:
            raise APIError(
                ErrorCode.CONFLICT,
                f"Artwork {item.artwork_id} is not ready.",
                status_code=409,
            )
        if not artwork.storage_bucket or not artwork.storage_key:
            raise APIError(
                ErrorCode.CONFLICT,
                f"Artwork {item.artwork_id} has no stored file.",
                status_code=409,
            )
        worker_items.append(
            {
                "artwork_id": str(item.artwork_id),
                "bucket": artwork.storage_bucket,
                "key": artwork.storage_key,
                "copies": item.copies,
                "rotate_deg": item.rotate_deg,
            }
        )

    gang_sheet = GangSheet(
        project_id=payload.project_id,
        status=GangSheetStatus.PENDING,
        sheet_width_mm=payload.sheet_width_mm,
        spacing_mm=payload.spacing_mm,
        dpi=payload.dpi,
        items=[
            {
                "artwork_id": str(item.artwork_id),
                "copies": item.copies,
                "rotate_deg": item.rotate_deg,
            }
            for item in payload.items
        ],
    )
    session.add(gang_sheet)
    await session.flush()  # assign gang_sheet.id

    gang_sheet.task_id = queue.enqueue_gang_sheet(
        gang_sheet.id,
        payload.project_id,
        _mm_to_px(payload.sheet_width_mm, payload.dpi),
        _mm_to_px(payload.spacing_mm, payload.dpi),
        payload.dpi,
        worker_items,
    )
    await session.commit()
    await session.refresh(gang_sheet)
    return SuccessResponse(
        data=GangSheetResponse.model_validate(gang_sheet), request_id=request_id_ctx.get()
    )


@router.get(
    "/{gang_sheet_id}",
    response_model=SuccessResponse[GangSheetDetailResponse],
    summary="Get a gang sheet's status, with a signed download URL once ready",
)
async def get_gang_sheet(
    gang_sheet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[GangSheetDetailResponse]:
    gang_sheet = await session.get(GangSheet, gang_sheet_id)
    if gang_sheet is None:
        raise APIError(ErrorCode.NOT_FOUND, "Gang sheet not found.", status_code=404)
    await load_owned_project(session, user, gang_sheet.project_id)  # authorize

    await _reconcile(gang_sheet, session)
    data = GangSheetDetailResponse.model_validate(gang_sheet)
    if gang_sheet.status == GangSheetStatus.READY and gang_sheet.storage_key:
        data.download_url = storage.create_presigned_download(
            gang_sheet.storage_bucket, gang_sheet.storage_key, settings.s3_signed_url_ttl_seconds
        )
    return SuccessResponse(data=data, request_id=request_id_ctx.get())


async def _reconcile(gang_sheet: GangSheet, session: AsyncSession) -> None:
    """Fold the worker's Celery state into the gang_sheets row. Best-effort;
    never raises."""
    if gang_sheet.status in _TERMINAL or not gang_sheet.task_id:
        return
    try:
        state, result = queue.get_job_state(gang_sheet.task_id)
    except Exception:
        return  # broker unreachable — leave the row unchanged

    if state == "SUCCESS" and isinstance(result, dict):
        dpi = result.get("dpi", gang_sheet.dpi)
        gang_sheet.status = GangSheetStatus.READY
        gang_sheet.storage_bucket = result.get("bucket")
        gang_sheet.storage_key = result.get("key")
        gang_sheet.sheet_height_mm = _px_to_mm(result.get("sheet_height_px", 0), dpi)
        gang_sheet.layout = [
            {
                "artwork_id": p["artwork_id"],
                "x": _px_to_mm(p["x"], dpi),
                "y": _px_to_mm(p["y"], dpi),
                "width": _px_to_mm(p["width"], dpi),
                "height": _px_to_mm(p["height"], dpi),
                "rotate_deg": p["rotate_deg"],
            }
            for p in result.get("placements", [])
        ]
    elif state == "FAILURE":
        gang_sheet.status = GangSheetStatus.FAILED
        gang_sheet.error_message = str(result)[:1000]
    else:
        return

    await session.commit()
    await session.refresh(gang_sheet)
