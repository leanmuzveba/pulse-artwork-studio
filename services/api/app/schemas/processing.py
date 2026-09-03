"""Processing-job schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import JobOperation, JobStatus


class JobCreateRequest(BaseModel):
    project_id: uuid.UUID
    artwork_id: uuid.UUID
    operation: JobOperation
    parameters: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    artwork_id: uuid.UUID
    result_artwork_id: uuid.UUID | None
    operation: JobOperation
    status: JobStatus
    progress: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
