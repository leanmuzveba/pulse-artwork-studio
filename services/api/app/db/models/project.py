from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import ProjectStatus

if TYPE_CHECKING:
    from app.db.models.artwork import Artwork
    from app.db.models.user import User


class Project(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, native_enum=False, length=32),
        default=ProjectStatus.ACTIVE,
        nullable=False,
    )

    owner: Mapped[User] = relationship(back_populates="projects")
    artworks: Mapped[list[Artwork]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
