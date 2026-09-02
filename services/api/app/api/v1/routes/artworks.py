"""Artworks — signed-URL upload orchestration and metadata.

Flow (nested under /projects/{project_id}/artworks):
  1. POST .../upload-url   -> validate, create an 'uploading' artwork, return a
                              presigned PUT URL. The browser uploads straight to
                              object storage — bytes never touch the API.
  2. PUT <upload_url>       -> client uploads the file to storage directly.
  3. POST .../{id}/confirm -> verify the object exists, record metadata, mark ready.
Originals are immutable: this only ever creates original artworks; processing
operations create new derived artworks in a later step.
"""

from __future__ import annotations

import uuid

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, load_owned_artwork, load_owned_project
from app.core.config import get_settings
from app.core.errors import APIError, ErrorCode
from app.core.logging import request_id_ctx
from app.db.enums import ArtworkKind, ArtworkStatus
from app.db.models import Artwork, User
from app.db.session import get_session
from app.schemas.artwork import (
    ArtworkConfirmRequest,
    ArtworkDetailResponse,
    ArtworkResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.common import SuccessResponse
from app.services import storage

router = APIRouter()
settings = get_settings()


@router.post(
    "/{project_id}/artworks/upload-url",
    response_model=SuccessResponse[UploadUrlResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Request a signed URL to upload an original artwork",
)
async def create_upload_url(
    project_id: uuid.UUID,
    payload: UploadUrlRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[UploadUrlResponse]:
    await load_owned_project(session, user, project_id)

    content_type = payload.content_type.lower()
    if content_type not in settings.allowed_upload_mime_set:
        raise APIError(
            ErrorCode.UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type '{content_type}'. Allowed: "
            f"{', '.join(sorted(settings.allowed_upload_mime_set))}.",
            status_code=415,
        )
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if payload.size_bytes is not None and payload.size_bytes > max_bytes:
        raise APIError(
            ErrorCode.PAYLOAD_TOO_LARGE,
            f"File is larger than the {settings.max_upload_mb} MB limit.",
            status_code=413,
        )

    bucket = settings.s3_bucket_originals
    artwork = Artwork(
        project_id=project_id,
        kind=ArtworkKind.ORIGINAL,
        status=ArtworkStatus.UPLOADING,
        original_filename=payload.filename,
        mime_type=content_type,
        size_bytes=payload.size_bytes,
        storage_bucket=bucket,
    )
    session.add(artwork)
    await session.flush()  # assign artwork.id
    key = storage.build_original_key(project_id, artwork.id, payload.filename)
    artwork.storage_key = key
    await session.commit()
    await session.refresh(artwork)

    ttl = settings.s3_signed_url_ttl_seconds
    upload_url = storage.create_presigned_upload(bucket, key, content_type, ttl)
    data = UploadUrlResponse(
        artwork_id=artwork.id,
        upload_url=upload_url,
        storage_key=key,
        bucket=bucket,
        expires_in=ttl,
        required_headers={"Content-Type": content_type},
    )
    return SuccessResponse(data=data, request_id=request_id_ctx.get())


@router.post(
    "/{project_id}/artworks/{artwork_id}/confirm",
    response_model=SuccessResponse[ArtworkResponse],
    summary="Confirm an upload completed and record metadata",
)
async def confirm_artwork(
    project_id: uuid.UUID,
    artwork_id: uuid.UUID,
    payload: ArtworkConfirmRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ArtworkResponse]:
    artwork = await load_owned_artwork(session, user, project_id, artwork_id)

    try:
        meta = storage.head_object(artwork.storage_bucket, artwork.storage_key)
    except (BotoCoreError, ClientError) as exc:
        raise APIError(
            ErrorCode.SERVICE_UNAVAILABLE,
            "Object storage is unavailable. Please try again shortly.",
            status_code=503,
        ) from exc
    if meta is None:
        raise APIError(
            ErrorCode.CONFLICT,
            "No uploaded file found. Upload the file to the signed URL first.",
            status_code=409,
        )

    artwork.status = ArtworkStatus.READY
    if meta.get("size_bytes") is not None:
        artwork.size_bytes = meta["size_bytes"]
    if payload.checksum:
        artwork.checksum = payload.checksum
    if payload.width is not None:
        artwork.width = payload.width
    if payload.height is not None:
        artwork.height = payload.height
    if payload.source_dpi is not None:
        artwork.source_dpi = payload.source_dpi
    await session.commit()
    await session.refresh(artwork)
    return SuccessResponse(
        data=ArtworkResponse.model_validate(artwork), request_id=request_id_ctx.get()
    )


@router.get(
    "/{project_id}/artworks",
    response_model=SuccessResponse[list[ArtworkResponse]],
    summary="List a project's artworks",
)
async def list_artworks(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[list[ArtworkResponse]]:
    await load_owned_project(session, user, project_id)
    result = await session.scalars(
        select(Artwork)
        .where(Artwork.project_id == project_id)
        .order_by(Artwork.created_at.desc())
    )
    artworks = [ArtworkResponse.model_validate(a) for a in result.all()]
    return SuccessResponse(data=artworks, request_id=request_id_ctx.get())


@router.get(
    "/{project_id}/artworks/{artwork_id}",
    response_model=SuccessResponse[ArtworkDetailResponse],
    summary="Get an artwork with a signed download URL",
)
async def get_artwork(
    project_id: uuid.UUID,
    artwork_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SuccessResponse[ArtworkDetailResponse]:
    artwork = await load_owned_artwork(session, user, project_id, artwork_id)
    data = ArtworkDetailResponse.model_validate(artwork)
    if artwork.status == ArtworkStatus.READY and artwork.storage_key:
        data.download_url = storage.create_presigned_download(
            artwork.storage_bucket, artwork.storage_key, settings.s3_signed_url_ttl_seconds
        )
    return SuccessResponse(data=data, request_id=request_id_ctx.get())
