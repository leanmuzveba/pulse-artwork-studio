from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.enums import PlanTier

if TYPE_CHECKING:
    from app.db.models.user import User


class Entitlement(UUIDMixin, TimestampMixin, Base):
    """A user's plan and usage limits. Modelled from day one; billing activates
    in Phase 5. One row per user."""

    __tablename__ = "entitlements"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    plan: Mapped[PlanTier] = mapped_column(
        SAEnum(PlanTier, native_enum=False, length=16),
        default=PlanTier.FREE,
        nullable=False,
    )
    limits: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict
    )

    user: Mapped[User] = relationship(back_populates="entitlement")
