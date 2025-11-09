"""Initial schema for works/chapters/ttranslations tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "works",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source_meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "work_id",
            sa.Integer(),
            sa.ForeignKey("works.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "chapter_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "chapter_id",
            sa.Integer(),
            sa.ForeignKey("chapters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
        sa.Column("model_config_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("cache_policy", sa.String(length=16), nullable=False, server_default="reuse"),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("cost_cents", sa.Integer(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_chapter_translations_chapter_id",
        "chapter_translations",
        ["chapter_id"],
        unique=False,
    )

    op.create_table(
        "translation_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "chapter_translation_id",
            sa.Integer(),
            sa.ForeignKey("chapter_translations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start", sa.Integer(), nullable=False),
        sa.Column("end", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("tgt", sa.Text(), nullable=False),
        sa.Column("flags", sa.JSON(), nullable=True),
        sa.Column("cache_key", sa.String(length=128), nullable=True),
        sa.Column("src_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_translation_segments_chapter_translation_id",
        "translation_segments",
        ["chapter_translation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_translation_segments_chapter_translation_id", table_name="translation_segments")
    op.drop_table("translation_segments")
    op.drop_index("ix_chapter_translations_chapter_id", table_name="chapter_translations")
    op.drop_table("chapter_translations")
    op.drop_table("chapters")
    op.drop_table("works")
