from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from agents.translation_agent import TranslationAgent
from app.config import settings
from app.models import Chapter, ChapterTranslation, TranslationSegment
from services.exceptions import SegmentNotFoundError
from services.prompt import PromptService
from services.translation_stream import TranslationStreamService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain event types
# ---------------------------------------------------------------------------


@dataclass
class TranslationStatusEvent:
    chapter_translation_id: int
    status: str


@dataclass
class SegmentStartEvent:
    chapter_translation_id: int
    segment_id: int
    order_index: int
    start: int
    end: int
    src: str


@dataclass
class SegmentDeltaEvent:
    chapter_translation_id: int
    segment_id: int
    order_index: int
    delta: str


@dataclass
class SegmentCompleteEvent:
    chapter_translation_id: int
    segment_id: int
    order_index: int
    text: str


@dataclass
class TranslationCompleteEvent:
    chapter_translation_id: int
    status: str


@dataclass
class TranslationErrorEvent:
    chapter_translation_id: int
    error: str
    segment_id: int | None = field(default=None)
    order_index: int | None = field(default=None)


TranslationEvent = (
    TranslationStatusEvent
    | SegmentStartEvent
    | SegmentDeltaEvent
    | SegmentCompleteEvent
    | TranslationCompleteEvent
    | TranslationErrorEvent
)


# ---------------------------------------------------------------------------
# Workflow service
# ---------------------------------------------------------------------------


class TranslationWorkflow:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._stream_service = TranslationStreamService(db)
        self._prompt_service = PromptService(db)

    def preflight_segment_check(
        self, chapter: Chapter, segment_id: int
    ) -> TranslationSegment:
        """Validate segment existence before opening an SSE stream.

        Raises SegmentNotFoundError if the segment does not exist or does not
        belong to this chapter's translation.  Must be called synchronously
        before EventSourceResponse is constructed so the error can be mapped
        to a proper HTTP 404.
        """
        from sqlalchemy import select

        translation = self._stream_service.get_or_create_translation(chapter.id)
        stmt = select(TranslationSegment).where(TranslationSegment.id == segment_id)
        segment = self.db.execute(stmt).scalars().first()
        if segment is None or segment.chapter_translation_id != translation.id:
            raise SegmentNotFoundError(f"segment {segment_id} not found")
        return segment

    def _resolve_agent(
        self,
        work_id: int,
        prompt_override: dict[str, Any] | None,
    ) -> TranslationAgent:
        """Resolve and construct a TranslationAgent for the given work.

        Mirrors the former _get_work_translation_agent logic verbatim:
        - fetches the work's assigned prompt
        - fetches the latest prompt version
        - applies prompt_override (template and model) if provided
        - falls back to settings.translation_model and settings.translation_api_key
        """
        prompt = self._prompt_service.get_prompt_for_work(work_id)

        system_prompt = None
        model = settings.translation_model
        if prompt_override:
            system_prompt = prompt_override.get("template") or None
            override_model = prompt_override.get("model")
            if isinstance(override_model, str) and override_model.strip():
                model = override_model
        elif prompt:
            versions, _, _, _ = self._prompt_service.get_prompt_versions(
                prompt.id, limit=1, offset=0
            )
            if versions:
                latest_version = versions[0]
                system_prompt = latest_version.template
                model = latest_version.model

        return TranslationAgent(
            model=model,
            api_key=settings.translation_api_key,
            api_base=settings.translation_api_base_url,
            chunk_chars=settings.translation_chunk_chars,
            context_window=settings.translation_context_segments,
            system_prompt=system_prompt,
        )

    async def start_or_resume(
        self,
        chapter: Chapter,
        work_id: int,
        *,
        prompt_override: dict[str, Any] | None,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[TranslationEvent, None]:
        """Start a new chapter translation or resume a pending one."""
        translation = self._stream_service.get_or_create_translation(chapter.id)
        segments = self._stream_service.ensure_segments(translation, chapter.normalized_text)
        is_not_complete = self._stream_service.first_pending_segment(segments) is not None

        agent = self._resolve_agent(work_id, prompt_override)
        work_prompt = self._prompt_service.get_prompt_for_work(work_id)

        logger.info(
            "Starting translation run",
            extra={
                "work_id": work_id,
                "chapter_id": chapter.id,
                "chapter_translation_id": translation.id,
                "model": agent.model,
                "chunk_chars": settings.translation_chunk_chars,
                "context_window": settings.translation_context_segments,
                "api_base": settings.translation_api_base_url,
                "has_custom_prompt": work_prompt is not None,
                "has_prompt_override": prompt_override is not None,
            },
        )

        if not is_not_complete:
            translation.status = "completed"
            self.db.add(translation)
            self.db.commit()
            yield TranslationCompleteEvent(
                chapter_translation_id=translation.id,
                status=translation.status,
            )
            return

        chapter_text = chapter.normalized_text
        segments_to_translate = [
            s for s in segments if self._stream_service.needs_translation(s)
        ]

        async for event in self._run_segment_loop(
            agent=agent,
            translation=translation,
            segments_to_translate=segments_to_translate,
            all_segments=list(segments),
            chapter_text=chapter_text,
            work_id=work_id,
            is_single_segment=False,
            instruction=None,
            current_translation=None,
            is_disconnected=is_disconnected,
        ):
            yield event

    async def retranslate_segment(
        self,
        chapter: Chapter,
        segment_id: int,
        work_id: int,
        *,
        prompt_override: dict[str, Any] | None,
        instruction: str | None,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[TranslationEvent, None]:
        """Retranslate a single segment."""
        from sqlalchemy import select

        translation = self._stream_service.get_or_create_translation(chapter.id)

        stmt = select(TranslationSegment).where(TranslationSegment.id == segment_id)
        segment = self.db.execute(stmt).scalars().first()

        if segment is None or segment.chapter_translation_id != translation.id:
            raise SegmentNotFoundError(f"segment {segment_id} not found")

        # Capture current translation before reset (for guided retranslation)
        current_tgt = segment.tgt if instruction else None

        # Reset the segment for retranslation
        self._stream_service.reset_segment(segment_id)
        segment = self.db.execute(stmt).scalars().first()

        agent = self._resolve_agent(work_id, prompt_override)
        chapter_text = chapter.normalized_text

        logger.info(
            "Starting segment retranslation",
            extra={
                "work_id": work_id,
                "chapter_id": chapter.id,
                "segment_id": segment_id,
                "chapter_translation_id": translation.id,
                "model": agent.model,
                "has_prompt_override": prompt_override is not None,
            },
        )

        all_segments = list(self._stream_service.get_segments_for_translation(translation.id))

        async for event in self._run_segment_loop(
            agent=agent,
            translation=translation,
            segments_to_translate=[segment],
            all_segments=all_segments,
            chapter_text=chapter_text,
            work_id=work_id,
            is_single_segment=True,
            instruction=instruction,
            current_translation=current_tgt,
            is_disconnected=is_disconnected,
        ):
            yield event

    async def _run_segment_loop(
        self,
        agent: TranslationAgent,
        translation: ChapterTranslation,
        segments_to_translate: list[TranslationSegment],
        all_segments: list[TranslationSegment],
        chapter_text: str,
        work_id: int,
        *,
        is_single_segment: bool,
        instruction: str | None,
        current_translation: str | None,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[TranslationEvent, None]:
        """Executes the per-segment translation loop."""
        current_segment = None
        try:
            if not is_single_segment:
                translation.status = "running"
                self.db.add(translation)
                self.db.commit()
                yield TranslationStatusEvent(
                    chapter_translation_id=translation.id,
                    status=translation.status,
                )

            for current in segments_to_translate:
                current_segment = current
                if await is_disconnected():
                    raise asyncio.CancelledError

                src = chapter_text[current.start : current.end]
                logger.info(
                    "Translate segment start",
                    extra={
                        "work_id": work_id,
                        "chapter_translation_id": translation.id,
                        "segment_id": current.id,
                        "order_index": current.order_index,
                        "segment_indices": {"start": current.start, "end": current.end},
                        "extracted_source_preview": src[:80] + "..." if len(src) > 80 else src,
                    },
                )
                yield SegmentStartEvent(
                    chapter_translation_id=translation.id,
                    segment_id=current.id,
                    order_index=current.order_index,
                    start=current.start,
                    end=current.end,
                    src=src,
                )

                context_segments = self._stream_service.build_context_window(
                    all_segments,
                    current,
                    chapter_text,
                    limit=agent.context_window,
                )

                collected = ""
                async for delta in agent.stream_segment(
                    src,
                    preceding_segments=context_segments,
                    instruction=instruction,
                    current_translation=current_translation,
                ):
                    if await is_disconnected():
                        raise asyncio.CancelledError
                    if not delta:
                        continue
                    collected += delta
                    yield SegmentDeltaEvent(
                        chapter_translation_id=translation.id,
                        segment_id=current.id,
                        order_index=current.order_index,
                        delta=delta,
                    )

                current.tgt = collected
                self.db.add(current)
                self.db.commit()
                yield SegmentCompleteEvent(
                    chapter_translation_id=translation.id,
                    segment_id=current.id,
                    order_index=current.order_index,
                    text=collected,
                )
                current_segment = None

            if not is_single_segment:
                translation.status = "completed"
                self.db.add(translation)
                self.db.commit()

            yield TranslationCompleteEvent(
                chapter_translation_id=translation.id,
                status=translation.status,
            )

        except asyncio.CancelledError:
            translation.status = "idle"
            self.db.add(translation)
            self.db.commit()
            raise
        except Exception as exc:  # pragma: no cover - surfaced via SSE
            translation.status = "error"
            self.db.add(translation)
            self.db.commit()
            if current_segment is not None:
                yield TranslationErrorEvent(
                    chapter_translation_id=translation.id,
                    error=str(exc),
                    segment_id=current_segment.id,
                    order_index=current_segment.order_index,
                )
            else:
                yield TranslationErrorEvent(
                    chapter_translation_id=translation.id,
                    error=str(exc),
                )
