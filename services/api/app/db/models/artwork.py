from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import ArtworkKind, ArtworkStatus

if TYPE_CHECKING:
    from app.db.models.processing_job import ProcessingJob
    from app.db.models.project import Project


class Artwork(UUIDMixin, TimestampMixin, Base):
    """An artwork asset. Originals are immutable; every processing operation
    produces a new derived Artwork pointing back to its parent."""

    __tablename__ = "artworks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    parent_artwork_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("artworks.id", ondelete="SET NULL"),
        index=True,
    )
    kind: Mapped[ArtworkKind] = mapped_column(
        SAEnum(ArtworkKind, native_enum=False, length=16),
        default=ArtworkKind.ORIGINAL,
        nullable=False,
    )
    status: Mapped[ArtworkStatus] = mapped_column(
        SAEnum(ArtworkStatus, native_enum=False, length=16),
        default=ArtworkStatus.UPLOADING,
        nullable=False,
    )

    # ---- File metadata ----
    original_filename: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    checksum: Mapped[str | None] = mapped_column(String(64))  # sha256 hex

    # ---- Image metadata ----
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    source_dpi: Mapped[int | None] = mapped_column(Integer)     # from the file's metadata
    effective_dpi: Mapped[int | None] = mapped_column(Integer)  # calculated for target size

    # ---- Storage (S3-compatible) ----
    storage_bucket: Mapped[str | None] = mapped_column(String(120))
    storage_key: Mapped[str | None] = mapped_column(String(512))

    project: Mapped[Project] = relationship(back_populates="artworks")
    parent: Mapped[Artwork | None] = relationship(remote_side="Artwork.id")
    jobs: Mapped[list[ProcessingJob]] = relationship(
        back_populates="artwork",
        foreign_keys="ProcessingJob.artwork_id",
        cascade="all, delete-orphan",
    )
