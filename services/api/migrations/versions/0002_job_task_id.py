"""add processing_jobs.task_id

Revision ID: 0002_job_task_id
Revises: 0001_initial
Create Date: 2026-09-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_job_task_id"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs", sa.Column("task_id", sa.String(155), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("processing_jobs", "task_id")
