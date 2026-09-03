from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import JobOperation, JobStatus

if TYPE_CHECKING:
    from app.db.models.artwork import Artwork
    from app.db.models.project import Project


class ProcessingJob(UUIDMixin, TimestampMixin, Base):
    """An async operation on an artwork.

    Lifecycle: REQUESTED -> QUEUED -> PROCESSING -> COMPLETED | FAILED (| CANCELLED)
    """

    __tablename__ = "processing_jobs"

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
    result_artwork_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("artworks.id", ondelete="SET NULL"),
    )

    operation: Mapped[JobOperation] = mapped_column(
        SAEnum(JobOperation, native_enum=False, length=32), nullable=False
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict
    )
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, native_enum=False, length=16),
        default=JobStatus.REQUESTED,
        index=True,
        nullable=False,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Celery task id, used to reconcile worker state into this row on poll.
    task_id: Mapped[str | None] = mapped_column(String(155))

    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship()
    artwork: Mapped[Artwork] = relationship(
        back_populates="jobs", foreign_keys=[artwork_id]
    )
    result_artwork: Mapped[Artwork | None] = relationship(foreign_keys=[result_artwork_id])
