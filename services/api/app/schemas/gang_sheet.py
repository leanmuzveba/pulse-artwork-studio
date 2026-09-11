"""Gang sheet schemas.

DTF roll-width presets are a client-side concept (send the resulting
`sheet_width_mm` directly) rather than a stored/validated enum here, so a new
preset never needs a migration. 300 / 330 / 600 mm correspond to the
roadmap's "30 / 33 / 60 cm" presets.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.enums import GangSheetStatus

MAX_GANG_SHEET_ITEMS = 40
MAX_GANG_SHEET_TOTAL_COPIES = 300


class GangSheetItem(BaseModel):
    artwork_id: uuid.UUID
    copies: int = Field(default=1, ge=1, le=100)
    rotate_deg: int = 0


class GangSheetCreateRequest(BaseModel):
    project_id: uuid.UUID
    sheet_width_mm: int = Field(ge=100, le=2000)
    spacing_mm: int = Field(default=5, ge=0, le=100)
    dpi: int = Field(default=300, ge=72, le=600)
    items: list[GangSheetItem] = Field(min_length=1, max_length=MAX_GANG_SHEET_ITEMS)

    @field_validator("items")
    @classmethod
    def _cap_total_copies(cls, items: list[GangSheetItem]) -> list[GangSheetItem]:
        total = sum(item.copies for item in items)
        if total > MAX_GANG_SHEET_TOTAL_COPIES:
            raise ValueError(
                f"Too many total copies ({total}); max is {MAX_GANG_SHEET_TOTAL_COPIES}."
            )
        return items


class GangSheetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: GangSheetStatus
    sheet_width_mm: int
    sheet_height_mm: int | None
    spacing_mm: int
    dpi: int
    items: list[dict[str, Any]]
    layout: list[dict[str, Any]] | None
    error_message: str | None
    created_at: datetime


class GangSheetDetailResponse(GangSheetResponse):
    download_url: str | None = None
