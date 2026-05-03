from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from agents.base_agent import SegmentContext, TraceContext
from agents.explanation_generator_v2 import get_explanation_generator_v2
from app.config import settings
from app.db import SessionLocal
from app.explanation_schemas import FACET_ORDER, ArtifactPayload, FacetType
from app.models import Chapter, TranslationSegment
from services.exceptions import SegmentNotFoundError, SegmentNotTranslatedError, SpanValidationError
from services.explanation_generation_registry import GenerationHandle, get_registry
from services.explanation_service import ExplanationService
from services.translation_stream import PARTIAL_TRANSLATION_FLAG, TranslationStreamService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


@dataclass
class FacetCompleteEvent:
    artifact_id: int
    facet_type: FacetType
    payload: dict  # serialised facet data


@dataclass
class ArtifactCompleteEvent:
    artifact_id: int
    status: str


@dataclass
class ArtifactErrorEvent:
    artifact_id: int
    error: str
    facet_type: FacetType | None = None


ExplanationV2Event = FacetCompleteEvent | ArtifactCompleteEvent | ArtifactErrorEvent

# Poll cadence when waiting on the subscriber queue. Small enough to notice
# client disconnects promptly, large enough to stay idle most of the time.
_SUBSCRIBE_POLL_INTERVAL_S = 1.0

# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class ExplanationWorkflowV2:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._explanation_svc = ExplanationService(db)
        self._translation_svc = TranslationStreamService(db)

    # ------------------------------------------------------------------
    # Preflight
    # ------------------------------------------------------------------

    def preflight_check(self, chapter: Chapter, segment_id: int) -> TranslationSegment:
        """Validate segment existence and translated state.

        Raises ``SegmentNotFoundError`` or ``SegmentNotTranslatedError``.
        Returns the segment on success.
        """
        translation = self._translation_svc.get_or_create_translation(chapter.id)
        segment = self._get_segment(segment_id)

        if segment is None or segment.chapter_translation_id != translation.id:
            raise SegmentNotFoundError(f"segment {segment_id} not found")

        if not self._is_translated(segment):
            raise SegmentNotTranslatedError(f"segment {segment_id} is not translated")

        return segment

    # ------------------------------------------------------------------
    # Span validation
    # ------------------------------------------------------------------

    def validate_span(
        self,
        segment_id: int,
        chapter: Chapter,
        span_start: int,
        span_end: int,
    ) -> None:
        """Raise ``SpanValidationError`` if the span is invalid for this segment."""
        if span_start >= span_end:
            raise SpanValidationError(
                f"span_start ({span_start}) must be less than span_end ({span_end})"
            )
        segment = self._get_segment(segment_id)
        if segment is None:
            raise SegmentNotFoundError(f"segment {segment_id} not found")
        source_text = chapter.normalized_text[segment.start : segment.end]
        if span_end > len(source_text):
            raise SpanValidationError(
                f"span_end ({span_end}) exceeds segment length ({len(source_text)})"
            )

    # ------------------------------------------------------------------
    # Start — create artifact, (re)start background generation
    # ------------------------------------------------------------------

    async def start(
        self,
        chapter: Chapter,
        segment_id: int,
        span_start: int,
        span_end: int,
        density: Literal["sparse", "dense"],
        *,
        jlpt_level: str | None = None,
        force: bool = False,
        facet_types: list[FacetType] | None = None,
    ) -> int:
        """Get or create an artifact and kick off background generation.

        If ``force=True`` any in-flight generation for this artifact is
        cancelled and the artifact is reset before a fresh run is started.
        When ``facet_types`` is also provided, only those facets are reset
        while the rest of the payload is preserved.

        Idempotent otherwise: if generation is already running, a duplicate
        call is a no-op.
        """
        self.validate_span(segment_id, chapter, span_start, span_end)
        translation = self._translation_svc.get_or_create_translation(chapter.id)
        artifact, _ = self._explanation_svc.get_or_create(
            segment_id,
            translation.id,
            density,
            span_start=span_start,
            span_end=span_end,
        )

        if force:
            registry = get_registry()
            superseded = ArtifactErrorEvent(artifact_id=artifact.id, error="superseded")
            await registry.cancel(artifact.id, emit_final=superseded)
            if facet_types:
                # Partial regeneration: reset only the specified facets.
                self._explanation_svc.regenerate_facets(artifact.id, facet_types)
                artifact = self._get_artifact_fresh(artifact.id) or artifact
            elif artifact.status != "pending" or artifact.payload_json is not None:
                self._explanation_svc.regenerate(artifact.id)
                artifact = self._get_artifact_fresh(artifact.id) or artifact

        # Only start generation when the artifact is not already terminal.
        if artifact.status not in ("complete", "error"):
            await self._ensure_generation(
                artifact.id,
                chapter.id,
                segment_id,
                span_start,
                span_end,
                density,
                jlpt_level=jlpt_level,
            )

        return artifact.id

    # ------------------------------------------------------------------
    # Subscribe — tail live events or replay from cache
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        chapter: Chapter,
        segment_id: int,
        span_start: int,
        span_end: int,
        density: Literal["sparse", "dense"],
        *,
        jlpt_level: str | None = None,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[ExplanationV2Event, None]:
        """Yield facet events for this artifact.

        Resolution order:

        1. Artifact is terminal (``complete``/``error``) → replay from the
           stored payload and close.
        2. Generation is already running → subscribe, replay buffered events,
           then tail.
        3. Otherwise → start a new generation task and subscribe to it.

        Client disconnection only unsubscribes; the background generation task
        continues to completion so its work is not wasted.
        """
        translation = self._translation_svc.get_or_create_translation(chapter.id)
        artifact, _ = self._explanation_svc.get_or_create(
            segment_id,
            translation.id,
            density,
            span_start=span_start,
            span_end=span_end,
        )

        if artifact.status in ("complete", "error") and artifact.payload_json:
            async for event in self._replay_from_cache(artifact.id, artifact.payload_json):
                yield event
            return

        registry = get_registry()
        handle = await registry.get(artifact.id)
        if handle is None or handle.done.is_set():
            handle = await self._ensure_generation(
                artifact.id,
                chapter.id,
                segment_id,
                span_start,
                span_end,
                density,
                jlpt_level=jlpt_level,
            )

        queue = handle.subscribe()
        try:
            while True:
                if await is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=_SUBSCRIBE_POLL_INTERVAL_S
                    )
                except TimeoutError:
                    continue
                if event is None:
                    return
                yield event
        finally:
            handle.unsubscribe(queue)

    # ------------------------------------------------------------------
    # Generation task machinery
    # ------------------------------------------------------------------

    async def _ensure_generation(
        self,
        artifact_id: int,
        chapter_id: int,
        segment_id: int,
        span_start: int,
        span_end: int,
        density: Literal["sparse", "dense"],
        *,
        jlpt_level: str | None = None,
    ) -> GenerationHandle:
        registry = get_registry()

        def producer_factory() -> AsyncGenerator[ExplanationV2Event, None]:
            return _run_generation(
                artifact_id=artifact_id,
                chapter_id=chapter_id,
                segment_id=segment_id,
                span_start=span_start,
                span_end=span_end,
                density=density,
                jlpt_level=jlpt_level,
            )

        return await registry.ensure(artifact_id, producer_factory)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_artifact_fresh(self, artifact_id: int):
        self.db.expire_all()
        return self._explanation_svc.get_by_id(artifact_id)

    async def _replay_from_cache(
        self, artifact_id: int, payload_json: dict
    ) -> AsyncGenerator[ExplanationV2Event, None]:
        """Yield FacetCompleteEvents for every complete facet in stored payload."""
        try:
            payload = ArtifactPayload.model_validate(payload_json)
        except Exception:
            logger.warning("ExplanationWorkflowV2: could not parse cached payload")
            yield ArtifactCompleteEvent(artifact_id=artifact_id, status="complete")
            return

        any_facet_error = False
        for facet_type in FACET_ORDER:
            entry = getattr(payload, facet_type)
            if entry is None:
                continue
            if entry.status == "complete" and entry.data is not None:
                yield FacetCompleteEvent(
                    artifact_id=artifact_id,
                    facet_type=facet_type,
                    payload=entry.data,
                )
            elif entry.status == "error":
                any_facet_error = True
                yield ArtifactErrorEvent(
                    artifact_id=artifact_id,
                    error=entry.error or "facet generation failed",
                    facet_type=facet_type,
                )
        yield ArtifactCompleteEvent(
            artifact_id=artifact_id,
            status="error" if any_facet_error else "complete",
        )

    def _get_segment(self, segment_id: int) -> TranslationSegment | None:
        from sqlalchemy import select

        stmt = select(TranslationSegment).where(TranslationSegment.id == segment_id)
        return self.db.execute(stmt).scalars().first()

    @staticmethod
    def _is_translated(segment: TranslationSegment) -> bool:
        flags = segment.flags or []
        if "whitespace" in flags or "empty" in flags:
            return False
        if PARTIAL_TRANSLATION_FLAG in flags:
            return False
        return bool((segment.tgt or "").strip())


# ---------------------------------------------------------------------------
# Background generation producer
# ---------------------------------------------------------------------------


def _get_preceding_context(segments, current, chapter_text, limit: int = 1):
    context = []
    for seg in reversed(segments):
        if seg.order_index >= current.order_index:
            continue
        tgt = (seg.tgt or "").strip()
        src = chapter_text[seg.start : seg.end].strip()
        if src and tgt:
            context.append(SegmentContext(src=src, tgt=tgt))
        if len(context) >= limit:
            break
    return list(reversed(context))


def _get_following_context(segments, current, chapter_text, limit: int = 1):
    context = []
    for seg in segments:
        if seg.order_index <= current.order_index:
            continue
        src = chapter_text[seg.start : seg.end].strip()
        if src:
            context.append(SegmentContext(src=src, tgt=(seg.tgt or "").strip()))
        if len(context) >= limit:
            break
    return context


async def _run_generation(
    *,
    artifact_id: int,
    chapter_id: int,
    segment_id: int,
    span_start: int,
    span_end: int,
    density: Literal["sparse", "dense"],
    jlpt_level: str | None = None,
) -> AsyncGenerator[ExplanationV2Event, None]:
    """Background producer: drives the LLM and persists each facet.

    Opens its own DB session because the request-scoped session that kicked
    this off will be closed long before generation finishes.
    """
    from sqlalchemy import select

    from app.models import Chapter, TranslationSegment

    with SessionLocal() as db:
        explanation_svc = ExplanationService(db)
        translation_svc = TranslationStreamService(db)

        try:
            chapter = (
                db.execute(select(Chapter).where(Chapter.id == chapter_id)).scalars().first()
            )
            segment = (
                db.execute(select(TranslationSegment).where(TranslationSegment.id == segment_id))
                .scalars()
                .first()
            )
            if chapter is None or segment is None:
                logger.warning(
                    "generation task: missing chapter or segment",
                    extra={
                        "artifact_id": artifact_id,
                        "chapter_id": chapter_id,
                        "segment_id": segment_id,
                    },
                )
                explanation_svc.mark_error(artifact_id, "chapter or segment not found")
                yield ArtifactErrorEvent(
                    artifact_id=artifact_id, error="chapter or segment not found"
                )
                return

            chapter_text = chapter.normalized_text
            source_text = chapter_text[segment.start : segment.end]
            translation_text = segment.tgt or ""

            all_segments = list(
                translation_svc.get_segments_for_translation(segment.chapter_translation_id)
            )
            preceding = _get_preceding_context(all_segments, segment, chapter_text)
            following = _get_following_context(all_segments, segment, chapter_text)

            # Resume support: replay facets already persisted in payload_json, and
            # skip them on the LLM pass.
            artifact = explanation_svc.get_by_id(artifact_id)
            done_facets: set[FacetType] = set()
            if artifact is not None and artifact.payload_json:
                try:
                    existing = ArtifactPayload.model_validate(artifact.payload_json)
                except Exception:
                    existing = ArtifactPayload()
                for facet_type in FACET_ORDER:
                    entry = getattr(existing, facet_type)
                    if entry is None:
                        continue
                    if entry.status == "complete" and entry.data is not None:
                        done_facets.add(facet_type)
                        yield FacetCompleteEvent(
                            artifact_id=artifact_id,
                            facet_type=facet_type,
                            payload=entry.data,
                        )

            if len(done_facets) == len(FACET_ORDER):
                yield _finalize_artifact(explanation_svc, artifact_id)
                return

            generator = get_explanation_generator_v2()

            trace = TraceContext(
                name="explain_v2.artifact",
                session_id=f"chapter_translation:{segment.chapter_translation_id}",
                metadata={
                    "artifact_id": artifact_id,
                    "chapter_id": chapter_id,
                    "chapter_translation_id": segment.chapter_translation_id,
                    "segment_id": segment_id,
                    "order_index": segment.order_index,
                    "span_start": span_start,
                    "span_end": span_end,
                    "density": density,
                    "jlpt_level": jlpt_level or settings.default_jlpt_level,
                },
                tags=["explanation", "v2", density],
            )

            async for facet_type, data, error in generator.generate_facets(
                segment_source=source_text,
                segment_translation=translation_text,
                span_start=span_start,
                span_end=span_end,
                density=density,
                jlpt_level=jlpt_level or settings.default_jlpt_level,
                preceding_segments=preceding,
                following_segments=following,
                skip_facets=done_facets,
                trace=trace,
            ):
                explanation_svc.update_facet(artifact_id, facet_type, data, error=error)
                if error:
                    yield ArtifactErrorEvent(
                        artifact_id=artifact_id,
                        error=error,
                        facet_type=facet_type,
                    )
                else:
                    yield FacetCompleteEvent(
                        artifact_id=artifact_id,
                        facet_type=facet_type,
                        payload=data.model_dump(),
                    )

            yield _finalize_artifact(explanation_svc, artifact_id)

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "ExplanationWorkflowV2: generation failed",
                extra={"artifact_id": artifact_id, "segment_id": segment_id},
            )
            try:
                explanation_svc.mark_error(artifact_id, str(exc))
            except Exception:
                logger.exception(
                    "ExplanationWorkflowV2: failed to persist terminal error status",
                    extra={"artifact_id": artifact_id},
                )
            yield ArtifactErrorEvent(artifact_id=artifact_id, error=str(exc))


def _finalize_artifact(svc: ExplanationService, artifact_id: int) -> ArtifactCompleteEvent:
    """Derive final artifact status from the persisted payload."""
    payload = svc.get_payload(artifact_id)
    failed: list[FacetType] = []
    for facet_type in FACET_ORDER:
        entry = getattr(payload, facet_type)
        if entry is not None and entry.status == "error":
            failed.append(facet_type)

    if failed:
        message = f"facet generation failed: {', '.join(failed)}"
        svc.mark_error(artifact_id, message)
        return ArtifactCompleteEvent(artifact_id=artifact_id, status="error")

    svc.mark_complete(artifact_id)
    return ArtifactCompleteEvent(artifact_id=artifact_id, status="complete")


# Keep exception imports available to callers that relied on the previous
# module surface.
__all__ = [
    "ArtifactCompleteEvent",
    "ArtifactErrorEvent",
    "ExplanationV2Event",
    "ExplanationWorkflowV2",
    "FacetCompleteEvent",
    "SegmentNotFoundError",
    "SegmentNotTranslatedError",
    "SpanValidationError",
]
