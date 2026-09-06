"""Export schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import ExportFormat, ExportStatus


class ExportCreateRequest(BaseModel):
    project_id: uuid.UUID
    artwork_id: uuid.UUID
    format: ExportFormat
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    artwork_id: uuid.UUID
    format: ExportFormat
    status: ExportStatus
    width: int | None
    height: int | None
    dpi: int | None
    error_message: str | None
    created_at: datetime


class ExportDetailResponse(ExportResponse):
    download_url: str | None = None
