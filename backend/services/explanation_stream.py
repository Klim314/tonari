from __future__ import annotations

from typing import List, Optional, Sequence, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chapter, ChapterTranslation, TranslationSegment


class ExplanationStreamService:
    """Helpers for streaming segment explanation generation."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_segment(self, segment_id: int) -> Optional[TranslationSegment]:
        """Get a segment by ID."""
        stmt = select(TranslationSegment).where(TranslationSegment.id == segment_id)
        return self.session.execute(stmt).scalars().first()

    def is_segment_translated(self, segment: TranslationSegment) -> bool:
        """Check if a segment has been translated."""
        flags = segment.flags or []
        if "whitespace" in flags or "empty" in flags:
            return False
        tgt_value = cast(Optional[str], segment.tgt)
        if tgt_value is None:
            return False
        return bool(tgt_value.strip())

    def get_segments_for_translation(self, translation_id: int) -> Sequence[TranslationSegment]:
        """Get all segments for a translation, ordered by index."""
        stmt = (
            select(TranslationSegment)
            .where(TranslationSegment.chapter_translation_id == translation_id)
            .order_by(TranslationSegment.order_index.asc(), TranslationSegment.id.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_preceding_segments(
        self,
        segments: Sequence[TranslationSegment],
        current: TranslationSegment,
        chapter_text: str,
        *,
        limit: int = 1,
    ) -> List[dict[str, str]]:
        """Get preceding segments as context.

        Args:
            segments: All segments in the translation.
            current: The current segment being explained.
            chapter_text: The full chapter text.
            limit: Maximum number of preceding segments to include.

        Returns:
            List of {"src": ..., "tgt": ...} dicts for preceding segments.
        """
        if limit <= 0:
            return []

        context: List[dict[str, str]] = []
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

    def get_following_segments(
        self,
        segments: Sequence[TranslationSegment],
        current: TranslationSegment,
        chapter_text: str,
        *,
        limit: int = 1,
    ) -> List[dict[str, str]]:
        """Get following segments as context.

        Args:
            segments: All segments in the translation.
            current: The current segment being explained.
            chapter_text: The full chapter text.
            limit: Maximum number of following segments to include.

        Returns:
            List of {"src": ..., "tgt": ...} dicts for following segments.
        """
        if limit <= 0:
            return []

        context: List[dict[str, str]] = []
        for segment in segments:
            if segment.order_index <= current.order_index:
                continue
            tgt = (segment.tgt or "").strip()
            # For following segments, we may not have translation yet, so check if exists
            src = chapter_text[segment.start : segment.end].strip()
            if not src:
                continue
            context.append({"src": src, "tgt": tgt})
            if len(context) >= limit:
                break
        return context

    def save_explanation(self, segment_id: int, explanation: str) -> Optional[TranslationSegment]:
        """Save generated explanation to a segment.

        Args:
            segment_id: ID of the segment.
            explanation: Markdown explanation text.

        Returns:
            Updated segment, or None if segment not found.
        """
        segment = self.get_segment(segment_id)
        if segment is None:
            return None

        segment.explanation = explanation
        self.session.add(segment)
        self.session.commit()
        self.session.refresh(segment)
        return segment
