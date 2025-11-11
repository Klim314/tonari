from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChapterTranslation, TranslationSegment
from app.translation_service import newline_segment_slices


class TranslationStreamService:
    """Helpers for initializing and tracking streaming chapter translations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_translation(self, chapter_id: int) -> ChapterTranslation:
        stmt = (
            select(ChapterTranslation)
            .where(ChapterTranslation.chapter_id == chapter_id)
            .order_by(ChapterTranslation.id.asc())
        )
        translation = self.session.execute(stmt).scalars().first()
        if translation is None:
            translation = ChapterTranslation(
                chapter_id=chapter_id,
                status="pending",
                cache_policy="reuse",
                params={},
            )
            self.session.add(translation)
            self.session.commit()
            self.session.refresh(translation)
        return translation

    def ensure_segments(self, translation: ChapterTranslation, chapter_text: str) -> List[TranslationSegment]:
        segments = self.list_segments(translation.id)
        if segments:
            return segments

        slices = newline_segment_slices(chapter_text)
        new_segments: List[TranslationSegment] = []
        for idx, slice_ in enumerate(slices):
            flags: list[str] = []
            if not slice_.requires_translation:
                flags.append("whitespace")
            new_segments.append(
                TranslationSegment(
                    chapter_translation_id=translation.id,
                    start=slice_.start,
                    end=slice_.end,
                    order_index=idx,
                    tgt="",
                    flags=flags,
                    cache_key=None,
                    src_hash="",
                )
            )
        self.session.add_all(new_segments)
        self.session.commit()
        return self.list_segments(translation.id)

    def list_segments(self, translation_id: int) -> List[TranslationSegment]:
        stmt = (
            select(TranslationSegment)
            .where(TranslationSegment.chapter_translation_id == translation_id)
            .order_by(TranslationSegment.order_index.asc(), TranslationSegment.id.asc())
        )
        return self.session.execute(stmt).scalars().all()

    @staticmethod
    def needs_translation(segment: TranslationSegment) -> bool:
        flags = segment.flags or []
        if "whitespace" in flags or "empty" in flags:
            return False
        return not bool(segment.tgt)

    def first_pending_segment(self, segments: List[TranslationSegment]) -> Optional[TranslationSegment]:
        for segment in segments:
            if self.needs_translation(segment):
                return segment
        return None
