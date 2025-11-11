from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint, Numeric
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
    prompt_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_config_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    cache_policy: Mapped[str] = mapped_column(String(16), default="reuse")
    params: Mapped[dict | None] = mapped_column(JSON, default=None)
    cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, default=None)

    chapter: Mapped[Chapter] = relationship("Chapter", back_populates="translations")
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
