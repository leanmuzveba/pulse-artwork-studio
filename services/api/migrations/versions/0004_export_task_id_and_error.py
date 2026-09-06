"""add exports.task_id and exports.error_message

Revision ID: 0004_export_task_id_and_error
Revises: 0003_job_result_data
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_export_task_id_and_error"
down_revision: Union[str, None] = "0003_job_result_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exports", sa.Column("task_id", sa.String(155), nullable=True))
    op.add_column("exports", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("exports", "error_message")
    op.drop_column("exports", "task_id")
