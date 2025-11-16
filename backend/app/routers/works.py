from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy.orm import Session as DBSession
from sse_starlette.sse import EventSourceResponse

from agents.explanation_agent import ExplanationAgent, get_explanation_agent
from agents.translation_agent import TranslationAgent
from app.config import settings
from app.db import SessionLocal
from app.prompt_overrides import (
    PromptOverrideExpiredError,
    PromptOverrideInvalidError,
    create_prompt_override_token,
    decode_prompt_override_token,
)
from app.schemas import (
    ChapterDetailOut,
    ChapterOut,
    ChapterPromptOverrideRequest,
    ChapterPromptOverrideResponse,
    ChapterScrapeErrorItem,
    ChapterScrapeRequest,
    ChapterScrapeResponse,
    ChapterTranslationStateOut,
    PaginatedChaptersOut,
    PaginatedWorksOut,
    TranslationSegmentOut,
    WorkImportRequest,
    WorkOut,
)
from app.scrapers.exceptions import ScraperError, ScraperNotFoundError
from app.translation_service import get_translation_agent
from services.chapters import ChaptersService
from services.exceptions import ChapterNotFoundError, ChapterScrapeError, WorkNotFoundError
from services.explanation_stream import ExplanationStreamService
from services.prompt import PromptService
from services.translation_stream import TranslationStreamService
from services.works import WorksService

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/", response_model=PaginatedWorksOut)
def search_works(q: str | None = Query(default=None), limit: int = 50, offset: int = 0):
    with SessionLocal() as db:
        works_service = WorksService(db)
        rows, total, limit, offset = works_service.search(q=q, limit=limit, offset=offset)
        return PaginatedWorksOut(
            items=[WorkOut.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.post("/import", response_model=WorkOut)
def import_work(req: WorkImportRequest):
    with SessionLocal() as db:
        works_service = WorksService(db)
        try:
            work = works_service.get_or_scrape_work(str(req.url), force=req.force)
        except ScraperNotFoundError:
            raise HTTPException(status_code=400, detail="no supported scraper found") from None
        except ScraperError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        return WorkOut.model_validate(work)


@router.get("/{work_id}", response_model=WorkOut)
def get_work(work_id: int):
    with SessionLocal() as db:
        works_service = WorksService(db)
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None
        return WorkOut.model_validate(work)


@router.get("/{work_id}/chapters", response_model=PaginatedChaptersOut)
def list_chapters_for_work(work_id: int, limit: int = 50, offset: int = 0):
    with SessionLocal() as db:
        works_service = WorksService(db)
        chapters_service = ChaptersService(db)
        try:
            works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None
        rows, total, limit, offset = chapters_service.get_chapters_for_work(
            work_id, limit=limit, offset=offset
        )
        return PaginatedChaptersOut(
            items=[ChapterOut.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get("/{work_id}/chapters/{chapter_id}", response_model=ChapterDetailOut)
def get_chapter_for_work(work_id: int, chapter_id: int):
    with SessionLocal() as db:
        works_service = WorksService(db)
        chapters_service = ChaptersService(db)
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None
        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None
        if chapter.work_id != work.id:
            raise HTTPException(status_code=404, detail="chapter not found") from None
        return ChapterDetailOut.model_validate(chapter)


@router.post("/{work_id}/scrape-chapters", response_model=ChapterScrapeResponse)
def request_chapter_scrape(work_id: int, payload: ChapterScrapeRequest):
    with SessionLocal() as db:
        works_service = WorksService(db)
        chapters_service = ChaptersService(db)
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None
        try:
            summary = chapters_service.scrape_work_for_chapters(
                work,
                start=payload.start,
                end=payload.end,
                force=payload.force,
            )
        except ChapterScrapeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        except ScraperNotFoundError:
            raise HTTPException(status_code=400, detail="no supported scraper found") from None

        return ChapterScrapeResponse(
            work_id=work.id,
            start=float(summary.start),
            end=float(summary.end),
            force=summary.force,
            status=summary.status,
            requested=summary.requested,
            created=summary.created,
            updated=summary.updated,
            skipped=summary.skipped,
            errors=[
                ChapterScrapeErrorItem(chapter=float(err.chapter), reason=err.reason)
                for err in summary.errors
            ],
        )


@router.get(
    "/{work_id}/chapters/{chapter_id}/translation", response_model=ChapterTranslationStateOut
)
def get_chapter_translation_state(work_id: int, chapter_id: int):
    with SessionLocal() as db:
        works_service = WorksService(db)
        chapters_service = ChaptersService(db)
        translation_service = TranslationStreamService(db)

        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None

        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        if chapter.work_id != work.id:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        translation = translation_service.get_or_create_translation(chapter.id)
        segments = translation_service.ensure_segments(translation, chapter.normalized_text)
        return _build_translation_state(chapter, translation, segments)


@router.delete(
    "/{work_id}/chapters/{chapter_id}/translation", response_model=ChapterTranslationStateOut
)
def reset_chapter_translation(work_id: int, chapter_id: int):
    with SessionLocal() as db:
        works_service = WorksService(db)
        chapters_service = ChaptersService(db)
        translation_service = TranslationStreamService(db)
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None
        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None
        if chapter.work_id != work.id:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        translation = translation_service.reset_translation(chapter.id)
        segments = translation_service.ensure_segments(
            translation, chapter.normalized_text, force=True
        )
        return _build_translation_state(chapter, translation, segments)


@router.post("/{work_id}/chapters/{chapter_id}/regenerate-segments")
def regenerate_chapter_segments(work_id: int, chapter_id: int):
    """Regenerate all segments for a chapter, discarding existing translations.

    This endpoint deletes all existing segments for all translations of the chapter
    and recreates them based on the current chapter text. This is useful when the
    chapter source text changes and needs to be re-segmented.
    """
    with SessionLocal() as db:
        works_service = WorksService(db)
        chapters_service = ChaptersService(db)
        translation_service = TranslationStreamService(db)
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None
        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None
        if chapter.work_id != work.id:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        translation_service.regenerate_chapter_segments(chapter)
        translation = translation_service.get_or_create_translation(chapter.id)
        segments = list(translation_service.get_segments_for_translation(translation.id))
        return _build_translation_state(chapter, translation, segments)


def _resolve_prompt_override(token: str | None, work_id: int, chapter_id: int):
    if not token:
        return None
    try:
        payload = decode_prompt_override_token(token)
    except PromptOverrideExpiredError:
        raise HTTPException(status_code=400, detail="prompt override expired") from None
    except PromptOverrideInvalidError:
        raise HTTPException(status_code=400, detail="prompt override token invalid") from None

    payload_work_id = payload.get("work_id")
    payload_chapter_id = payload.get("chapter_id")
    if payload_work_id != work_id or payload_chapter_id != chapter_id:
        raise HTTPException(
            status_code=400, detail="prompt override token does not match chapter"
        ) from None
    if not payload.get("template") or not payload.get("model"):
        raise HTTPException(status_code=400, detail="prompt override missing prompt data") from None
    return payload


@router.post(
    "/{work_id}/chapters/{chapter_id}/prompt-overrides",
    response_model=ChapterPromptOverrideResponse,
)
def create_chapter_prompt_override(
    work_id: int, chapter_id: int, payload: ChapterPromptOverrideRequest
):
    """Create a signed prompt override token for a single translation run."""
    with SessionLocal() as db:
        works_service = WorksService(db)
        chapters_service = ChaptersService(db)

        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None

        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        if chapter.work_id != work.id:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        token = create_prompt_override_token(
            work_id=work.id,
            chapter_id=chapter.id,
            model=payload.model,
            template=payload.template,
            parameters=payload.parameters,
        )

        expires_at = datetime.fromtimestamp(token.expires_at, tz=timezone.utc)
        return ChapterPromptOverrideResponse(token=token.token, expires_at=expires_at)




def _sse_event(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


def _get_work_translation_agent(
    work_id: int, db: DBSession, *, prompt_override: dict[str, Any] | None = None
) -> TranslationAgent:
    """Get a translation agent with the work's selected prompt, or default if none selected."""
    prompt_service = PromptService(db)
    prompt = prompt_service.get_prompt_for_work(work_id)

    # Get the latest version if a prompt is assigned
    system_prompt = None
    model = settings.translation_model  # Default model
    if prompt_override:
        system_prompt = prompt_override.get("template") or None
        override_model = prompt_override.get("model")
        if isinstance(override_model, str) and override_model.strip():
            model = override_model
    elif prompt:
        versions, _, _, _ = prompt_service.get_prompt_versions(prompt.id, limit=1, offset=0)
        if versions:
            latest_version = versions[0]
            system_prompt = latest_version.template
            model = latest_version.model

    # Create agent with work-specific prompt/model or defaults
    return TranslationAgent(
        model=model,
        api_key=settings.translation_api_key,
        api_base=settings.translation_api_base_url,
        chunk_chars=settings.translation_chunk_chars,
        context_window=settings.translation_context_segments,
        system_prompt=system_prompt,
    )


def _build_translation_state(chapter, translation, segments) -> ChapterTranslationStateOut:
    chapter_text = chapter.normalized_text
    payload_segments = []
    for segment in segments:
        payload_segments.append(
            TranslationSegmentOut(
                id=segment.id,
                start=segment.start,
                end=segment.end,
                order_index=segment.order_index,
                src=chapter_text[segment.start : segment.end],
                tgt=segment.tgt or "",
                flags=segment.flags or [],
            )
        )

    return ChapterTranslationStateOut(
        chapter_translation_id=translation.id,
        status=translation.status,
        segments=payload_segments,
    )


async def _translate_segments_stream(
    db: DBSession,
    request: Request,
    translation_agent: TranslationAgent,
    translation_service: TranslationStreamService,
    translation,
    segments_to_translate,
    all_segments,
    chapter_text: str,
    work_id: int,
    is_single_segment: bool = False,
):
    """
    Unified async generator for translating segments (either full chapter or single segment).

    Args:
        db: Database session
        request: FastAPI request object
        translation_agent: Translation agent
        translation_service: Translation service
        translation: ChapterTranslation object
        segments_to_translate: List of segments that need translation
        all_segments: All segments for context window building
        chapter_text: Full chapter text
        work_id: Work ID for logging
        is_single_segment: If True, don't set translation.status to completed at the end
    """
    current_segment = None
    try:
        # For full chapter, set status to running
        if not is_single_segment:
            translation.status = "running"
            db.add(translation)
            db.commit()
            yield _sse_event(
                "translation-status",
                {"chapter_translation_id": translation.id, "status": translation.status},
            )

        for current in segments_to_translate:
            current_segment = current
            if await request.is_disconnected():
                raise asyncio.CancelledError

            src = chapter_text[current.start : current.end]
            yield _sse_event(
                "segment-start",
                {
                    "chapter_translation_id": translation.id,
                    "segment_id": current.id,
                    "order_index": current.order_index,
                    "start": current.start,
                    "end": current.end,
                    "src": src,
                },
            )

            context_segments = translation_service.build_context_window(
                all_segments,
                current,
                chapter_text,
                limit=translation_agent.context_window,
            )

            collected = ""
            async for delta in translation_agent.stream_segment(
                src, preceding_segments=context_segments
            ):
                if await request.is_disconnected():
                    raise asyncio.CancelledError
                if not delta:
                    continue
                collected += delta
                yield _sse_event(
                    "segment-delta",
                    {
                        "chapter_translation_id": translation.id,
                        "segment_id": current.id,
                        "order_index": current.order_index,
                        "delta": delta,
                    },
                )

            current.tgt = collected
            db.add(current)
            db.commit()
            yield _sse_event(
                "segment-complete",
                {
                    "chapter_translation_id": translation.id,
                    "segment_id": current.id,
                    "order_index": current.order_index,
                    "text": collected,
                },
            )
            current_segment = None

        # Only mark translation as completed if this is a full chapter translation
        if not is_single_segment:
            translation.status = "completed"
            db.add(translation)
            db.commit()

        # Always emit completion event (for both full chapter and single segment)
        yield _sse_event(
            "translation-complete",
            {"chapter_translation_id": translation.id, "status": translation.status},
        )

    except asyncio.CancelledError:
        translation.status = "idle"
        db.add(translation)
        db.commit()
        raise
    except Exception as exc:  # pragma: no cover - surfaced via SSE
        translation.status = "error"
        db.add(translation)
        db.commit()
        if current_segment is not None:
            yield _sse_event(
                "translation-error",
                {
                    "chapter_translation_id": translation.id,
                    "segment_id": current_segment.id,
                    "order_index": current_segment.order_index,
                    "error": str(exc),
                },
            )
        else:
            yield _sse_event(
                "translation-error",
                {
                    "chapter_translation_id": translation.id,
                    "error": str(exc),
                },
            )


@router.get("/{work_id}/chapters/{chapter_id}/translate/stream")
async def stream_chapter_translation(
    work_id: int,
    chapter_id: int,
    request: Request,
    prompt_override_token: str | None = Query(default=None),
):
    db = SessionLocal()
    works_service = WorksService(db)
    chapters_service = ChaptersService(db)
    translation_service = TranslationStreamService(db)
    # TODO: Gate concurrent translators per chapter translation to avoid duplicate work.
    # TODO: Handle reset_chapter_translation invalidating in-flight segments (emit reset event instead of crashing).

    try:
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None

        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        if chapter.work_id != work.id:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        translation = translation_service.get_or_create_translation(chapter.id)
        segments = translation_service.ensure_segments(translation, chapter.normalized_text)
        is_not_complete = translation_service.first_pending_segment(segments) is not None

        prompt_service = PromptService(db)
        work_prompt = prompt_service.get_prompt_for_work(work_id)

        prompt_override = _resolve_prompt_override(prompt_override_token, work_id, chapter_id)

        translation_agent = _get_work_translation_agent(
            work_id, db, prompt_override=prompt_override
        )

        logger.info(
            "Starting translation run",
            extra={
                "work_id": work_id,
                "chapter_id": chapter_id,
                "chapter_translation_id": translation.id,
                "model": translation_agent.model,
                "chunk_chars": settings.translation_chunk_chars,
                "context_window": settings.translation_context_segments,
                "api_base": settings.translation_api_base_url,
                "has_custom_prompt": work_prompt is not None,
                "has_prompt_override": prompt_override is not None,
            },
        )

        if not is_not_complete:

            async def completed_generator():
                try:
                    translation.status = "completed"
                    db.add(translation)
                    db.commit()
                    yield _sse_event(
                        "translation-complete",
                        {"chapter_translation_id": translation.id, "status": translation.status},
                    )
                finally:
                    db.close()

            return EventSourceResponse(completed_generator())

        chapter_text = chapter.normalized_text
        segments_to_translate = [s for s in segments if translation_service.needs_translation(s)]

        async def event_generator():
            try:
                async for event in _translate_segments_stream(
                    db=db,
                    request=request,
                    translation_agent=translation_agent,
                    translation_service=translation_service,
                    translation=translation,
                    segments_to_translate=segments_to_translate,
                    all_segments=segments,
                    chapter_text=chapter_text,
                    work_id=work_id,
                    is_single_segment=False,
                ):
                    yield event
            finally:
                db.close()

        return EventSourceResponse(event_generator())

    except Exception:
        db.close()
        raise


@router.get("/{work_id}/chapters/{chapter_id}/segments/{segment_id}/retranslate/stream")
async def retranslate_segment(
    work_id: int,
    chapter_id: int,
    segment_id: int,
    request: Request,
    prompt_override_token: str | None = Query(default=None),
):
    """Retranslate a single segment in a chapter translation."""
    from sqlalchemy import select
    from app.models import TranslationSegment

    db = SessionLocal()
    works_service = WorksService(db)
    chapters_service = ChaptersService(db)
    translation_service = TranslationStreamService(db)

    try:
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None

        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        if chapter.work_id != work.id:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        translation = translation_service.get_or_create_translation(chapter.id)

        # Get the specific segment
        stmt = select(TranslationSegment).where(TranslationSegment.id == segment_id)
        segment = db.execute(stmt).scalars().first()

        if segment is None or segment.chapter_translation_id != translation.id:
            raise HTTPException(status_code=404, detail="segment not found") from None

        # Reset the segment for retranslation
        translation_service.reset_segment(segment_id)
        segment = db.execute(stmt).scalars().first()

        prompt_override = _resolve_prompt_override(prompt_override_token, work_id, chapter_id)

        translation_agent = _get_work_translation_agent(
            work_id, db, prompt_override=prompt_override
        )
        chapter_text = chapter.normalized_text

        logger.info(
            "Starting segment retranslation",
            extra={
                "work_id": work_id,
                "chapter_id": chapter_id,
                "segment_id": segment_id,
                "chapter_translation_id": translation.id,
                "model": translation_agent.model,
                "has_prompt_override": prompt_override is not None,
            },
        )

        # Get all segments for context
        all_segments = list(translation_service.get_segments_for_translation(translation.id))

        async def event_generator():
            try:
                async for event in _translate_segments_stream(
                    db=db,
                    request=request,
                    translation_agent=translation_agent,
                    translation_service=translation_service,
                    translation=translation,
                    segments_to_translate=[segment],
                    all_segments=all_segments,
                    chapter_text=chapter_text,
                    work_id=work_id,
                    is_single_segment=True,
                ):
                    yield event
            finally:
                db.close()

        return EventSourceResponse(event_generator())

    except Exception:
        if db:
            db.close()
        raise


@router.get("/{work_id}/chapters/{chapter_id}/segments/{segment_id}/explain/stream")
async def explain_segment(
    work_id: int,
    chapter_id: int,
    segment_id: int,
    request: Request,
):
    """Stream explanation for a translation segment."""
    from sqlalchemy import select

    from app.models import TranslationSegment

    db = SessionLocal()
    works_service = WorksService(db)
    chapters_service = ChaptersService(db)
    explanation_service = ExplanationStreamService(db)
    translation_service = TranslationStreamService(db)

    try:
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None

        try:
            chapter = chapters_service.get_chapter(chapter_id)
        except ChapterNotFoundError:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        if chapter.work_id != work.id:
            raise HTTPException(status_code=404, detail="chapter not found") from None

        translation = translation_service.get_or_create_translation(chapter.id)

        # Get the specific segment
        stmt = select(TranslationSegment).where(TranslationSegment.id == segment_id)
        segment = db.execute(stmt).scalars().first()

        if segment is None or segment.chapter_translation_id != translation.id:
            raise HTTPException(status_code=404, detail="segment not found") from None

        # Check if segment is translated
        if not explanation_service.is_segment_translated(segment):
            raise HTTPException(status_code=400, detail="segment is not translated") from None

        # Get the explanation agent (uses hardcoded prompt)
        explanation_agent = get_explanation_agent()

        chapter_text = chapter.normalized_text
        all_segments = list(translation_service.get_segments_for_translation(translation.id))

        # Get current segment text and translation
        current_source = chapter_text[segment.start : segment.end]
        current_translation = segment.tgt or ""

        # Get surrounding segments for context
        preceding_segments = explanation_service.get_preceding_segments(
            all_segments, segment, chapter_text, limit=1
        )
        following_segments = explanation_service.get_following_segments(
            all_segments, segment, chapter_text, limit=1
        )

        logger.info(
            "Starting segment explanation",
            extra={
                "work_id": work_id,
                "chapter_id": chapter_id,
                "segment_id": segment_id,
                "model": explanation_agent.model,
            },
        )

        async def event_generator():
            try:
                collected = ""
                try:
                    async for delta in explanation_agent.stream_explanation(
                        current_source,
                        current_translation,
                        preceding_segments=preceding_segments,
                        following_segments=following_segments,
                    ):
                        if await request.is_disconnected():
                            raise asyncio.CancelledError
                        if not delta:
                            continue
                        collected += delta
                        yield _sse_event(
                            "explanation-delta",
                            {
                                "segment_id": segment_id,
                                "delta": delta,
                            },
                        )

                    # Save the explanation to the database
                    explanation_service.save_explanation(segment_id, collected)

                    yield _sse_event(
                        "explanation-complete",
                        {
                            "segment_id": segment_id,
                            "explanation": collected,
                        },
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover
                    logger.exception("Explanation generation failed")
                    yield _sse_event(
                        "explanation-error",
                        {
                            "segment_id": segment_id,
                            "error": str(exc),
                        },
                    )
            finally:
                db.close()

        return EventSourceResponse(event_generator())

    except Exception:
        if db:
            db.close()
        raise
