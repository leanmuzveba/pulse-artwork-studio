"""add gang_sheets table

Revision ID: 0005_gang_sheets
Revises: 0004_export_task_id_and_error
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_gang_sheets"
down_revision: str | None = "0004_export_task_id_and_error"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _ts(name: str) -> sa.Column:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "gang_sheets",
        sa.Column("id", UUID, nullable=False),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "ready", "failed", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("sheet_width_mm", sa.Integer(), nullable=False),
        sa.Column("sheet_height_mm", sa.Integer(), nullable=True),
        sa.Column("spacing_mm", sa.Integer(), nullable=False),
        sa.Column("dpi", sa.Integer(), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("layout", postgresql.JSONB(), nullable=True),
        sa.Column("storage_bucket", sa.String(120), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("task_id", sa.String(155), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_gang_sheets"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_gang_sheets_project_id_projects", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_gang_sheets_project_id", "gang_sheets", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_gang_sheets_project_id", table_name="gang_sheets")
    op.drop_table("gang_sheets")
