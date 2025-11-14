from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.db import Base


class Work(Base):
    __tablename__ = "works"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_work_source_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512))
    source: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_meta: Mapped[dict | None] = mapped_column(JSON, default=None)

    chapters: Mapped[list["Chapter"]] = relationship("Chapter", back_populates="work")
    prompt_links: Mapped[list["WorkPrompt"]] = relationship(
        "WorkPrompt", back_populates="work", cascade="all, delete-orphan"
    )
    owned_prompts: Mapped[list["Prompt"]] = relationship("Prompt", back_populates="owner_work")


class Chapter(Base):
    __tablename__ = "chapters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("works.id", ondelete="CASCADE"))
    idx: Mapped[int] = mapped_column(Integer)
    sort_key: Mapped[Decimal] = mapped_column(Numeric(12, 4), index=True)
    title: Mapped[str] = mapped_column(String(512))
    normalized_text: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(128))

    work: Mapped[Work] = relationship("Work", back_populates="chapters")
    translations: Mapped[list["ChapterTranslation"]] = relationship(
        "ChapterTranslation", back_populates="chapter"
    )


class ChapterTranslation(Base):
    __tablename__ = "chapter_translations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    prompt_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_config_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    cache_policy: Mapped[str] = mapped_column(String(16), default="reuse")
    params: Mapped[dict | None] = mapped_column(JSON, default=None)
    model_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters_snapshot: Mapped[dict | None] = mapped_column(JSON, default=None)
    cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, default=None)

    chapter: Mapped[Chapter] = relationship("Chapter", back_populates="translations")
    prompt_version: Mapped["PromptVersion | None"] = relationship("PromptVersion")
    segments: Mapped[list["TranslationSegment"]] = relationship(
        "TranslationSegment", back_populates="chapter_translation"
    )


class TranslationSegment(Base):
    __tablename__ = "translation_segments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chapter_translation_id: Mapped[int] = mapped_column(
        ForeignKey("chapter_translations.id", ondelete="CASCADE"), index=True
    )
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(Integer)
    tgt: Mapped[str] = mapped_column(Text)  # target-language text for this segment
    flags: Mapped[list | None] = mapped_column(JSON, default=list)
    cache_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    src_hash: Mapped[str] = mapped_column(String(128))

    chapter_translation: Mapped[ChapterTranslation] = relationship(
        "ChapterTranslation", back_populates="segments"
    )


class Prompt(Base):
    __tablename__ = "prompts"
    __table_args__ = (UniqueConstraint("owner_work_id", "name", name="uq_prompt_owner_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_work_id: Mapped[int | None] = mapped_column(
        ForeignKey("works.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner_work: Mapped[Work | None] = relationship(
        "Work", back_populates="owned_prompts", foreign_keys=[owner_work_id]
    )
    versions: Mapped[list["PromptVersion"]] = relationship(
        "PromptVersion", back_populates="prompt", cascade="all, delete-orphan"
    )
    work_prompts: Mapped[list["WorkPrompt"]] = relationship(
        "WorkPrompt", back_populates="prompt", cascade="all, delete-orphan"
    )


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("prompt_id", "version_number", name="uq_prompt_version_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(128))
    template: Mapped[str] = mapped_column(Text)
    parameters: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    prompt: Mapped[Prompt] = relationship("Prompt", back_populates="versions")
    chapter_translations: Mapped[list[ChapterTranslation]] = relationship(
        "ChapterTranslation", back_populates="prompt_version"
    )


class WorkPrompt(Base):
    __tablename__ = "work_prompts"
    __table_args__ = (UniqueConstraint("work_id", name="uq_work_prompt_work_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("works.id", ondelete="CASCADE"), index=True)
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"), index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)

    work: Mapped[Work] = relationship("Work", back_populates="prompt_links")
    prompt: Mapped[Prompt] = relationship("Prompt", back_populates="work_prompts")
