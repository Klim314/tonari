"""Add source/source_id columns and unique constraint to works."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_work_source_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("works", sa.Column("source", sa.String(length=64), nullable=True))
    op.add_column("works", sa.Column("source_id", sa.String(length=128), nullable=True))
    op.create_index("ix_works_source", "works", ["source"], unique=False)
    op.create_index("ix_works_source_id", "works", ["source_id"], unique=False)
    op.create_unique_constraint("uq_work_source_id", "works", ["source", "source_id"])


def downgrade() -> None:
    op.drop_constraint("uq_work_source_id", "works", type_="unique")
    op.drop_index("ix_works_source_id", table_name="works")
    op.drop_index("ix_works_source", table_name="works")
    op.drop_column("works", "source_id")
    op.drop_column("works", "source")
