from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import ExportFormat, ExportStatus

if TYPE_CHECKING:
    from app.db.models.artwork import Artwork
    from app.db.models.project import Project


class Export(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "exports"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    artwork_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("artworks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    format: Mapped[ExportFormat] = mapped_column(
        SAEnum(ExportFormat, native_enum=False, length=8), nullable=False
    )
    status: Mapped[ExportStatus] = mapped_column(
        SAEnum(ExportStatus, native_enum=False, length=16),
        default=ExportStatus.PENDING,
        nullable=False,
    )
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    dpi: Mapped[int | None] = mapped_column(Integer)

    storage_bucket: Mapped[str | None] = mapped_column(String(120))
    storage_key: Mapped[str | None] = mapped_column(String(512))

    project: Mapped[Project] = relationship()
    artwork: Mapped[Artwork] = relationship()
