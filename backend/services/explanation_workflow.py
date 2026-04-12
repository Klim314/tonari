from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from agents.explanation_agent import get_explanation_agent
from app.models import Chapter, TranslationSegment
from services.exceptions import SegmentNotFoundError, SegmentNotTranslatedError
from services.explanation_stream import ExplanationStreamService
from services.translation_stream import TranslationStreamService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain event types
# ---------------------------------------------------------------------------


@dataclass
class ExplanationDeltaEvent:
    segment_id: int
    delta: str


@dataclass
class ExplanationCompleteEvent:
    segment_id: int
    explanation: str


@dataclass
class ExplanationErrorEvent:
    segment_id: int
    error: str


ExplanationEvent = ExplanationDeltaEvent | ExplanationCompleteEvent | ExplanationErrorEvent


# ---------------------------------------------------------------------------
# Workflow service
# ---------------------------------------------------------------------------


class ExplanationWorkflow:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._explanation_service = ExplanationStreamService(db)
        self._translation_service = TranslationStreamService(db)

    def preflight_check(self, chapter: Chapter, segment_id: int) -> TranslationSegment:
        """Validate segment existence and translated state.

        Raises SegmentNotFoundError or SegmentNotTranslatedError as appropriate.
        Returns the segment on success.
        """
        translation = self._translation_service.get_or_create_translation(chapter.id)
        segment = self._explanation_service.get_segment(segment_id)

        if segment is None or segment.chapter_translation_id != translation.id:
            raise SegmentNotFoundError(f"segment {segment_id} not found")

        if not self._explanation_service.is_segment_translated(segment):
            raise SegmentNotTranslatedError(f"segment {segment_id} is not translated")

        return segment

    async def explain_segment(
        self,
        chapter: Chapter,
        segment_id: int,
        *,
        force: bool = False,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[ExplanationEvent, None]:
        """Generate or return cached explanation for a translated segment."""
        translation = self._translation_service.get_or_create_translation(chapter.id)
        segment = self._explanation_service.get_segment(segment_id)

        if segment is None or segment.chapter_translation_id != translation.id:
            raise SegmentNotFoundError(f"segment {segment_id} not found")

        if not self._explanation_service.is_segment_translated(segment):
            raise SegmentNotTranslatedError(f"segment {segment_id} is not translated")

        if force:
            self._explanation_service.clear_explanation(segment_id)
            # Refresh segment to reflect cleared explanation
            from sqlalchemy import select
            stmt = select(TranslationSegment).where(TranslationSegment.id == segment_id)
            segment = self.db.execute(stmt).scalars().first()
        elif segment.explanation:
            logger.info(
                "Returning cached explanation",
                extra={"segment_id": segment_id, "chapter_id": chapter.id},
            )
            yield ExplanationDeltaEvent(segment_id=segment_id, delta=segment.explanation)
            yield ExplanationCompleteEvent(
                segment_id=segment_id, explanation=segment.explanation
            )
            return

        explanation_agent = get_explanation_agent()
        chapter_text = chapter.normalized_text
        all_segments = list(
            self._translation_service.get_segments_for_translation(translation.id)
        )

        current_source = chapter_text[segment.start : segment.end]
        current_translation = segment.tgt or ""

        logger.info(
            "Explain segment context",
            extra={
                "chapter_id": chapter.id,
                "segment_id": segment_id,
                "order_index": segment.order_index,
                "segment_indices": {"start": segment.start, "end": segment.end},
                "extracted_source_preview": current_source[:80] + "..."
                if len(current_source) > 80
                else current_source,
                "extracted_target_preview": current_translation[:80] + "..."
                if len(current_translation) > 80
                else current_translation,
            },
        )

        preceding_segments = self._explanation_service.get_preceding_segments(
            all_segments, segment, chapter_text, limit=1
        )
        following_segments = self._explanation_service.get_following_segments(
            all_segments, segment, chapter_text, limit=1
        )

        logger.info(
            "Starting segment explanation",
            extra={
                "chapter_id": chapter.id,
                "segment_id": segment_id,
                "model": explanation_agent.model,
                "order_index": segment.order_index,
                "force": force,
            },
        )

        collected = ""
        try:
            async for delta in explanation_agent.stream_explanation(
                current_source,
                current_translation,
                preceding_segments=preceding_segments,
                following_segments=following_segments,
            ):
                if await is_disconnected():
                    raise asyncio.CancelledError
                if not delta:
                    continue
                collected += delta
                yield ExplanationDeltaEvent(segment_id=segment_id, delta=delta)

            logger.info(
                "Saving segment explanation",
                extra={
                    "chapter_id": chapter.id,
                    "segment_id": segment_id,
                    "order_index": segment.order_index,
                    "source_preview": current_source[:80]
                    + ("..." if len(current_source) > 80 else ""),
                    "translation_preview": current_translation[:80]
                    + ("..." if len(current_translation) > 80 else ""),
                    "explanation_preview": collected[:120]
                    + ("..." if len(collected) > 120 else ""),
                    "explanation_sha256": hashlib.sha256(collected.encode("utf-8")).hexdigest()
                    if collected
                    else None,
                    "force": force,
                },
            )
            self._explanation_service.save_explanation(segment_id, collected)
            yield ExplanationCompleteEvent(segment_id=segment_id, explanation=collected)

        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover
            logger.exception("Explanation generation failed")
            yield ExplanationErrorEvent(segment_id=segment_id, error=str(exc))
