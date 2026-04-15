from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from agents.base_agent import SegmentContext
from agents.explanation_generator_v2 import get_explanation_generator_v2
from app.explanation_schemas import FACET_ORDER, ArtifactPayload, FacetType
from app.models import Chapter, TranslationSegment
from services.exceptions import SegmentNotFoundError, SegmentNotTranslatedError, SpanValidationError
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
        """Raise ``SpanValidationError`` if the span is invalid for this segment.

        Checks:
        - ``span_start < span_end``
        - ``span_end <= len(segment_source)``
        """
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
    # Start — create artifact, return ID
    # ------------------------------------------------------------------

    def start(
        self,
        chapter: Chapter,
        segment_id: int,
        span_start: int,
        span_end: int,
        density: Literal["sparse", "dense"],
        *,
        force: bool = False,
    ) -> int:
        """Get or create an explanation artifact and return its ID.

        If ``force=True`` and the artifact already exists it is reset to
        ``pending`` so the next stream will regenerate it.
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

        if force and artifact.status != "pending":
            artifact = self._explanation_svc.regenerate(artifact.id)

        return artifact.id

    # ------------------------------------------------------------------
    # Stream — drive generation, yield events
    # ------------------------------------------------------------------

    async def stream(
        self,
        chapter: Chapter,
        segment_id: int,
        span_start: int,
        span_end: int,
        density: Literal["sparse", "dense"],
        *,
        is_disconnected: Callable[[], Awaitable[bool]],
    ) -> AsyncGenerator[ExplanationV2Event, None]:
        """Generate (or replay cached) explanation facets as SSE events.

        On a cache hit (status=complete) all facets are replayed from the
        stored payload without calling the LLM.  On a cache miss the LLM
        generates each facet sequentially and persists them as they complete.
        """
        translation = self._translation_svc.get_or_create_translation(chapter.id)
        artifact, _ = self._explanation_svc.get_or_create(
            segment_id,
            translation.id,
            density,
            span_start=span_start,
            span_end=span_end,
        )

        # Cache hit — replay stored facets and close.
        if artifact.status in ("complete", "error") and artifact.payload_json:
            async for event in self._replay_from_cache(artifact.id, artifact.payload_json):
                yield event
            return

        # Partial progress — replay what's already saved, then generate the rest.
        # Errored facets are intentionally *not* emitted here: they are not in
        # done_facets, so generate_facets will retry them, and surfacing a stale
        # error for a facet about to succeed is misleading.
        done_facets: set[FacetType] = set()
        if artifact.payload_json:
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
                        artifact_id=artifact.id,
                        facet_type=facet_type,
                        payload=entry.data,
                    )

        # If every facet is already complete, finalize and close without calling the LLM.
        if len(done_facets) == len(FACET_ORDER):
            yield self._finalize_artifact(artifact.id)
            return

        # Drive generation for the remaining facets.
        segment = self._get_segment(segment_id)
        chapter_text = chapter.normalized_text
        source_text = chapter_text[segment.start : segment.end]
        translation_text = segment.tgt or ""

        all_segments = list(self._translation_svc.get_segments_for_translation(translation.id))
        preceding = self._get_preceding_context(all_segments, segment, chapter_text)
        following = self._get_following_context(all_segments, segment, chapter_text)

        generator = get_explanation_generator_v2()

        try:
            async for facet_type, data, error in generator.generate_facets(
                segment_source=source_text,
                segment_translation=translation_text,
                span_start=span_start,
                span_end=span_end,
                density=density,
                preceding_segments=preceding,
                following_segments=following,
                skip_facets=done_facets,
            ):
                if await is_disconnected():
                    raise asyncio.CancelledError

                self._explanation_svc.update_facet(artifact.id, facet_type, data, error=error)

                if error:
                    yield ArtifactErrorEvent(
                        artifact_id=artifact.id,
                        error=error,
                        facet_type=facet_type,
                    )
                else:
                    yield FacetCompleteEvent(
                        artifact_id=artifact.id,
                        facet_type=facet_type,
                        payload=data.model_dump(),
                    )

            yield self._finalize_artifact(artifact.id)

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "ExplanationWorkflowV2: generation failed",
                extra={"artifact_id": artifact.id, "segment_id": segment_id},
            )
            self._explanation_svc.mark_error(artifact.id, str(exc))
            yield ArtifactErrorEvent(artifact_id=artifact.id, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _finalize_artifact(self, artifact_id: int) -> ArtifactCompleteEvent:
        """Derive final artifact status from the persisted payload.

        Reading from payload_json (rather than tracking in-memory flags) keeps
        the artifact status in lock-step with what actually landed on disk —
        including retries that succeeded after an earlier failure.
        """
        payload = self._explanation_svc.get_payload(artifact_id)
        failed: list[FacetType] = []
        for facet_type in FACET_ORDER:
            entry = getattr(payload, facet_type)
            if entry is not None and entry.status == "error":
                failed.append(facet_type)

        if failed:
            message = f"facet generation failed: {', '.join(failed)}"
            self._explanation_svc.mark_error(artifact_id, message)
            return ArtifactCompleteEvent(artifact_id=artifact_id, status="error")

        self._explanation_svc.mark_complete(artifact_id)
        return ArtifactCompleteEvent(artifact_id=artifact_id, status="complete")

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

    @staticmethod
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

    @staticmethod
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
