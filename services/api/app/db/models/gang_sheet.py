from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import GangSheetStatus

if TYPE_CHECKING:
    from app.db.models.project import Project


class GangSheet(UUIDMixin, TimestampMixin, Base):
    """A multi-artwork auto-nested DTF print sheet, composited from the
    project's artworks onto one roll-width canvas.

    Lifecycle: PENDING -> READY | FAILED (mirrors Export).
    """

    __tablename__ = "gang_sheets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[GangSheetStatus] = mapped_column(
        SAEnum(GangSheetStatus, native_enum=False, length=16),
        default=GangSheetStatus.PENDING,
        nullable=False,
    )

    sheet_width_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    # Computed by the auto-nest packer on success — the sheet's fixed width is
    # a roll-width preset, but its length grows to fit whatever was placed.
    sheet_height_mm: Mapped[int | None] = mapped_column(Integer)
    spacing_mm: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    dpi: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    # Requested items: [{artwork_id, copies, rotate_deg}].
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    # Computed on success: [{artwork_id, x, y, width, height, rotate_deg}] (mm).
    layout: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    storage_bucket: Mapped[str | None] = mapped_column(String(120))
    storage_key: Mapped[str | None] = mapped_column(String(512))

    # Celery task id, used to reconcile worker state into this row on poll.
    task_id: Mapped[str | None] = mapped_column(String(155))
    error_message: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship()
