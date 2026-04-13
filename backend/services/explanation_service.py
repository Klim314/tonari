from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.explanation_schemas import AnyFacetData, ArtifactPayload, FacetEntry, FacetType
from app.models import TranslationExplanation, TranslationSegment

logger = logging.getLogger(__name__)


class ExplanationService:
    """Manages the lifecycle of TranslationExplanation artifacts.

    All span coordinates are segment-relative character offsets.
    ``span_start`` and ``span_end`` are ``None`` for segment-level explanations.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_artifact(
        self,
        segment_id: int,
        density: Literal["sparse", "dense"],
        *,
        span_start: int | None = None,
        span_end: int | None = None,
    ) -> TranslationExplanation | None:
        """Return an existing artifact matching the cache key, or ``None``."""
        stmt = select(TranslationExplanation).where(
            TranslationExplanation.anchor_segment_id == segment_id,
            TranslationExplanation.density == density,
            TranslationExplanation.span_start == span_start,
            TranslationExplanation.span_end == span_end,
        )
        return self.session.execute(stmt).scalars().first()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def get_or_create(
        self,
        segment_id: int,
        chapter_translation_id: int,
        density: Literal["sparse", "dense"],
        *,
        span_start: int | None = None,
        span_end: int | None = None,
    ) -> tuple[TranslationExplanation, bool]:
        """Return ``(artifact, created)``.

        If no artifact exists for the cache key a new ``pending`` row is
        created and ``created=True`` is returned.  If one already exists it is
        returned unchanged with ``created=False``.
        """
        # Lock the segment row for the duration of this transaction so that
        # concurrent get_or_create calls for the same segment are serialized,
        # preventing a TOCTOU race on the check-then-insert below.
        self.session.execute(
            select(TranslationSegment)
            .where(TranslationSegment.id == segment_id)
            .with_for_update()
        )

        existing = self.get_artifact(segment_id, density, span_start=span_start, span_end=span_end)
        if existing is not None:
            return (existing, False)

        analysis_unit_type = "sentence" if span_start is not None else "segment"
        artifact = TranslationExplanation(
            analysis_unit_type=analysis_unit_type,
            anchor_segment_id=segment_id,
            chapter_translation_id=chapter_translation_id,
            density=density,
            span_start=span_start,
            span_end=span_end,
            status="pending",
            payload_json=None,
        )
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        logger.info(
            "ExplanationService: created artifact",
            extra={
                "artifact_id": artifact.id,
                "segment_id": segment_id,
                "density": density,
                "span_start": span_start,
                "span_end": span_end,
            },
        )
        return (artifact, True)

    def update_facet(
        self,
        artifact_id: int,
        facet_type: FacetType,
        data: AnyFacetData | None,
        *,
        error: str | None = None,
    ) -> None:
        """Persist a completed (or errored) facet into the artifact payload."""
        artifact = self._get_by_id(artifact_id)
        if artifact is None:
            return

        payload = self._load_payload(artifact)
        entry = FacetEntry(
            status="error" if error else "complete",
            data=data.model_dump() if data is not None else None,
            error=error,
        )
        setattr(payload, facet_type, entry)
        artifact.payload_json = payload.model_dump()
        artifact.status = "generating"
        self.session.add(artifact)
        self.session.commit()

    def mark_complete(self, artifact_id: int) -> None:
        """Set artifact status to ``complete``."""
        artifact = self._get_by_id(artifact_id)
        if artifact is None:
            return
        artifact.status = "complete"
        self.session.add(artifact)
        self.session.commit()

    def mark_error(self, artifact_id: int, message: str) -> None:
        """Set artifact status to ``error`` and record the message."""
        artifact = self._get_by_id(artifact_id)
        if artifact is None:
            return
        artifact.status = "error"
        payload = self._load_payload(artifact)
        payload.error = message
        artifact.payload_json = payload.model_dump()
        self.session.add(artifact)
        self.session.commit()

    def regenerate(self, artifact_id: int) -> TranslationExplanation | None:
        """Reset an artifact to ``pending`` and clear its payload.

        The next SSE stream request will re-drive generation.
        """
        artifact = self._get_by_id(artifact_id)
        if artifact is None:
            return None
        artifact.status = "pending"
        artifact.payload_json = None
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_by_id(self, artifact_id: int) -> TranslationExplanation | None:
        stmt = select(TranslationExplanation).where(TranslationExplanation.id == artifact_id)
        return self.session.execute(stmt).scalars().first()

    @staticmethod
    def _load_payload(artifact: TranslationExplanation) -> ArtifactPayload:
        """Parse stored payload JSON, or return an empty payload if absent."""
        if artifact.payload_json:
            try:
                return ArtifactPayload.model_validate(artifact.payload_json)
            except Exception:
                logger.warning(
                    "ExplanationService: could not parse stored payload, resetting",
                    extra={"artifact_id": artifact.id},
                )
        return ArtifactPayload()
