"""add_chapter_sort_key

Revision ID: 9b336c20d318
Revises: 0002_add_work_source_fields
Create Date: 2025-11-10 12:23:04.868500
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "9b336c20d318"
down_revision = "0002_add_work_source_fields"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "chapters",
        sa.Column("sort_key", sa.Numeric(precision=12, scale=4), nullable=True),
    )
    op.execute("UPDATE chapters SET sort_key = idx")
    op.alter_column("chapters", "sort_key", nullable=False)
    op.create_index(op.f("ix_chapters_sort_key"), "chapters", ["sort_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chapters_sort_key"), table_name="chapters")
    op.drop_column("chapters", "sort_key")
