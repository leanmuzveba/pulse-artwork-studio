"""initial schema: users, projects, artworks, processing_jobs, exports, entitlements, audit_logs

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _ts(name: str) -> sa.Column:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID, nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "suspended", "deleted", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", UUID, nullable=False),
        sa.Column("owner_id", UUID, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "archived", "deleted", native_enum=False, length=32),
            nullable=False,
        ),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"],
            name="fk_projects_owner_id_users", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    op.create_table(
        "artworks",
        sa.Column("id", UUID, nullable=False),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("parent_artwork_id", UUID, nullable=True),
        sa.Column(
            "kind",
            sa.Enum("original", "derived", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("uploading", "ready", "failed", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("source_dpi", sa.Integer(), nullable=True),
        sa.Column("effective_dpi", sa.Integer(), nullable=True),
        sa.Column("storage_bucket", sa.String(120), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_artworks"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_artworks_project_id_projects", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_artwork_id"], ["artworks.id"],
            name="fk_artworks_parent_artwork_id_artworks", ondelete="SET NULL",
        ),
    )
    op.create_index("ix_artworks_project_id", "artworks", ["project_id"])
    op.create_index("ix_artworks_parent_artwork_id", "artworks", ["parent_artwork_id"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", UUID, nullable=False),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("artwork_id", UUID, nullable=False),
        sa.Column("result_artwork_id", UUID, nullable=True),
        sa.Column(
            "operation",
            sa.Enum(
                "metadata", "enhance", "upscale", "background_removal", "vectorize",
                "halftone", "embroidery", "dtf_check",
                native_enum=False, length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "parameters", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "requested", "queued", "processing", "completed", "failed", "cancelled",
                native_enum=False, length=16,
            ),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_processing_jobs"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_processing_jobs_project_id_projects", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artwork_id"], ["artworks.id"],
            name="fk_processing_jobs_artwork_id_artworks", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["result_artwork_id"], ["artworks.id"],
            name="fk_processing_jobs_result_artwork_id_artworks", ondelete="SET NULL",
        ),
    )
    op.create_index("ix_processing_jobs_project_id", "processing_jobs", ["project_id"])
    op.create_index("ix_processing_jobs_artwork_id", "processing_jobs", ["artwork_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])

    op.create_table(
        "exports",
        sa.Column("id", UUID, nullable=False),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("artwork_id", UUID, nullable=False),
        sa.Column(
            "format",
            sa.Enum("png", "svg", "pdf", native_enum=False, length=8),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "ready", "failed", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("dpi", sa.Integer(), nullable=True),
        sa.Column("storage_bucket", sa.String(120), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_exports"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name="fk_exports_project_id_projects", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artwork_id"], ["artworks.id"],
            name="fk_exports_artwork_id_artworks", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_exports_project_id", "exports", ["project_id"])
    op.create_index("ix_exports_artwork_id", "exports", ["artwork_id"])

    op.create_table(
        "entitlements",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column(
            "plan",
            sa.Enum(
                "free", "professional", "business", "enterprise",
                native_enum=False, length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "limits", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_entitlements"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_entitlements_user_id_users", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", name="uq_entitlements_user_id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=True),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "context", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_audit_logs_user_id_users", ondelete="SET NULL",
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("entitlements")
    op.drop_table("exports")
    op.drop_table("processing_jobs")
    op.drop_table("artworks")
    op.drop_table("projects")
    op.drop_table("users")
