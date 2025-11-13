"""work_prompt_tables

Revision ID: 8c8dfd2915ad
Revises: 26a2bf9dc2bf
Create Date: 2025-11-13 09:06:46.487426
"""
from __future__ import annotations

revision = "8c8dfd2915ad"
down_revision = '26a2bf9dc2bf'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

LEGACY_TEMPLATE = """
You are a professional Japanese-to-English literary translator.
You will be provided an excerpt of text from a novel, including some context from the preceding section which you are to translate.
Maintain the original tone and theme of the source text.
Provide a final English translation without commentary.
""".strip()


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS work_prompts CASCADE")
    op.execute("DROP TABLE IF EXISTS prompt_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS prompts CASCADE")

    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_work_id", sa.Integer(), sa.ForeignKey("works.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("owner_work_id", "name", name="uq_prompt_owner_name"),
    )
    op.create_index(op.f("ix_prompts_owner_work_id"), "prompts", ["owner_work_id"], unique=False)

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prompt_id",
            sa.Integer(),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("prompt_id", "version_number", name="uq_prompt_version_number"),
    )
    op.create_index(
        op.f("ix_prompt_versions_prompt_id"), "prompt_versions", ["prompt_id"], unique=False
    )

    op.create_table(
        "work_prompts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "work_id",
            sa.Integer(),
            sa.ForeignKey("works.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_id",
            sa.Integer(),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("work_id", name="uq_work_prompt_work_id"),
    )
    op.create_index(op.f("ix_work_prompts_work_id"), "work_prompts", ["work_id"], unique=False)
    op.create_index(op.f("ix_work_prompts_prompt_id"), "work_prompts", ["prompt_id"], unique=False)

    op.create_foreign_key(
        "fk_chapter_translations_prompt_version",
        "chapter_translations",
        "prompt_versions",
        ["prompt_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        sa.text(
            """
            UPDATE chapter_translations
            SET model_snapshot = COALESCE(model_snapshot, :model_snapshot),
                template_snapshot = COALESCE(template_snapshot, :template_snapshot),
                parameters_snapshot = COALESCE(parameters_snapshot, '{}'::json)
            """
        ).bindparams(
            model_snapshot="legacy-global",
            template_snapshot=LEGACY_TEMPLATE,
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_chapter_translations_prompt_version",
        "chapter_translations",
        type_="foreignkey",
    )

    op.drop_index(op.f("ix_work_prompts_prompt_id"), table_name="work_prompts")
    op.drop_index(op.f("ix_work_prompts_work_id"), table_name="work_prompts")
    op.drop_table("work_prompts")

    op.drop_index(op.f("ix_prompt_versions_prompt_id"), table_name="prompt_versions")
    op.drop_table("prompt_versions")

    op.drop_index(op.f("ix_prompts_owner_work_id"), table_name="prompts")
    op.drop_table("prompts")
