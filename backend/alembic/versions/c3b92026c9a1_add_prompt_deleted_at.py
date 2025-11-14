"""add prompt deleted_at column

Revision ID: c3b92026c9a1
Revises: 8c8dfd2915ad
Create Date: 2025-11-14 10:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c3b92026c9a1"
down_revision = "8c8dfd2915ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prompts",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prompts", "deleted_at")
