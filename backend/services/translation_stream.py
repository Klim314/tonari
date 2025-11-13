from __future__ import annotations

from typing import List, Optional, Sequence, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chapter, ChapterTranslation, TranslationSegment
from app.translation_service import hash_text, newline_segment_slices


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

    def ensure_segments(
        self, translation: ChapterTranslation, chapter_text: str, *, force: bool = False
    ) -> List[TranslationSegment]:
        """Ensure translation segments mirror the chapter text.

        - When segments already exist and `force` is false, they are returned as-is.
        - When no segments exist or `force` is true, the chapter text is re-sliced into
          newline-delimited chunks and fresh `TranslationSegment` rows are created.
        """
        segments = self.get_segments_for_translation(translation.id)
        if segments and not force:
            return list(segments)

        if force and segments:
            self.session.query(TranslationSegment).filter(
                TranslationSegment.chapter_translation_id == translation.id
            ).delete(synchronize_session=False)
            self.session.commit()

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
                    src_hash=hash_text(slice_.text),
                )
            )
        self.session.add_all(new_segments)
        self.session.commit()
        return list(self.get_segments_for_translation(translation.id))

    def get_segments_for_translation(self, translation_id: int) -> Sequence[TranslationSegment]:
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
        tgt_value = cast(Optional[str], segment.tgt)
        if tgt_value is None:
            return True
        return not tgt_value.strip()

    def first_pending_segment(
        self, segments: Sequence[TranslationSegment]
    ) -> Optional[TranslationSegment]:
        for segment in segments:
            if self.needs_translation(segment):
                return segment
        return None

    def build_context_window(
        self,
        segments: List[TranslationSegment],
        current: TranslationSegment,
        chapter_text: str,
        *,
        limit: int = 3,
    ) -> List[dict[str, str]]:
        if limit <= 0:
            return []
        context: List[dict[str, str]] = []
        # Keep the logic intentionally simple; segment counts are small.
        for segment in reversed(segments):
            if segment.order_index >= current.order_index:
                continue
            tgt = (segment.tgt or "").strip()
            if not tgt:
                continue
            src = chapter_text[segment.start : segment.end].strip()
            if not src:
                continue
            context.append({"src": src, "tgt": tgt})
            if len(context) >= limit:
                break
        return list(reversed(context))

    def reset_translation(self, chapter_id: int) -> ChapterTranslation:
        translation = self.get_or_create_translation(chapter_id)
        self.session.query(TranslationSegment).filter(
            TranslationSegment.chapter_translation_id == translation.id
        ).delete(synchronize_session=False)
        translation.status = "pending"
        translation.cost_cents = None
        translation.meta = None
        self.session.add(translation)
        self.session.commit()
        self.session.refresh(translation)
        return translation

    def regenerate_chapter_segments(self, chapter: Chapter) -> None:
        """Delete and regenerate segments for the most recent translation of a chapter.

        This is useful when chapter text changes and segments need to be
        re-segmented with new character positions. Only regenerates for the most
        recent translation (which is the one displayed on the chapter page).
        """
        stmt = (
            select(ChapterTranslation)
            .where(ChapterTranslation.chapter_id == chapter.id)
            .order_by(ChapterTranslation.id.desc())
            .limit(1)
        )
        translation = self.session.execute(stmt).scalars().first()
        if translation is None:
            return

        # Delete existing segments
        self.session.query(TranslationSegment).filter(
            TranslationSegment.chapter_translation_id == translation.id
        ).delete(synchronize_session=False)
        self.session.commit()

        # Recreate segments
        self.ensure_segments(translation, chapter.normalized_text, force=True)
