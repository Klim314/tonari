"""add_scrape_jobs

Revision ID: 6727872b16b1
Revises: a21635cef4ae
Create Date: 2026-01-16 03:06:13.839360
"""
from __future__ import annotations

revision = "6727872b16b1"
down_revision = 'a21635cef4ae'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa



def upgrade() -> None:
    op.create_unique_constraint('uq_chapter_work_sort_key', 'chapters', ['work_id', 'sort_key'])

    # Guard: table may already exist from prior create_all() usage
    conn = op.get_bind()
    inspector = inspect(conn)
    if "scrape_jobs" not in inspector.get_table_names():
        op.create_table(
            "scrape_jobs",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "work_id",
                sa.Integer,
                sa.ForeignKey("works.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("start", sa.Numeric(12, 4), nullable=False),
            sa.Column("end", sa.Numeric(12, 4), nullable=False),
            sa.Column(
                "status", sa.String(32), nullable=False, server_default="pending", index=True
            ),
            sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
            sa.Column("total", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("scrape_jobs")
    op.drop_constraint('uq_chapter_work_sort_key', 'chapters', type_='unique')
