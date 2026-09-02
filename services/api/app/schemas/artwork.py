"""Artwork upload + metadata schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ArtworkKind, ArtworkStatus


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int | None = Field(default=None, ge=0)


class UploadUrlResponse(BaseModel):
    artwork_id: uuid.UUID
    method: str = "PUT"
    upload_url: str
    storage_key: str
    bucket: str
    expires_in: int
    required_headers: dict[str, str]


class ArtworkConfirmRequest(BaseModel):
    checksum: str | None = Field(default=None, max_length=64)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    source_dpi: int | None = Field(default=None, ge=0)


class ArtworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    parent_artwork_id: uuid.UUID | None
    kind: ArtworkKind
    status: ArtworkStatus
    original_filename: str | None
    mime_type: str | None
    size_bytes: int | None
    width: int | None
    height: int | None
    source_dpi: int | None
    created_at: datetime


class ArtworkDetailResponse(ArtworkResponse):
    download_url: str | None = None
