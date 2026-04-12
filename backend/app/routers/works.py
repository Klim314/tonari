from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.db import SessionLocal
from app.models import ChapterTranslation
from app.prompt_overrides import (
    PromptOverrideExpiredError,
    PromptOverrideInvalidError,
    create_prompt_override_token,
    decode_prompt_override_token,
)
from app.schemas import (
    BatchSegmentUpdateRequest,
    ChapterDetailOut,
    ChapterGroupOut,
    ChapterOrGroup,
    ChapterOut,
    ChapterPromptOverrideRequest,
    ChapterPromptOverrideResponse,
    ChapterScrapeRequest,
    ChapterScrapeResponse,
    ChaptersWithGroupsResponse,
    ChapterTranslationStateOut,
    PaginatedWorksOut,
    TranslationSegmentOut,
    WorkImportRequest,
    WorkOut,
)
from app.scrapers.exceptions import ScraperError, ScraperNotFoundError
from services.chapter_groups import ChapterGroupsService
from services.chapters import ChaptersService
from services.exceptions import (
    ChapterNotFoundError,
    SegmentNotFoundError,
    SegmentNotTranslatedError,
    WorkNotFoundError,
)
from services.explanation_workflow import (
    ExplanationCompleteEvent,
    ExplanationDeltaEvent,
    ExplanationErrorEvent,
    ExplanationEvent,
    ExplanationWorkflow,
)
from services.scrape_manager import ScrapeManager
from services.translation_stream import TranslationStreamService
from services.translation_workflow import (
    SegmentCompleteEvent,
    SegmentDeltaEvent,
    SegmentStartEvent,
    TranslationCompleteEvent,
    TranslationErrorEvent,
    TranslationEvent,
    TranslationStatusEvent,
    TranslationWorkflow,
)
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


def _get_completed_translation_chapter_ids(db, chapter_ids: list[int]) -> set[int]:
    """Get set of chapter IDs that have a completed translation."""
    if not chapter_ids:
        return set()
    from sqlalchemy import select

    stmt = select(ChapterTranslation.chapter_id).where(
        ChapterTranslation.chapter_id.in_(chapter_ids),
        ChapterTranslation.status == "completed",
    )
    return set(db.execute(stmt).scalars().all())


@router.get("/{work_id}/chapters", response_model=ChaptersWithGroupsResponse)
def list_chapters_for_work(work_id: int, limit: int = 50, offset: int = 0):
    with SessionLocal() as db:
        works_service = WorksService(db)
        groups_service = ChapterGroupsService(db)
        try:
            works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None

        items, total_chapters, total_groups, total_items, limit, offset = (
            groups_service.get_chapters_with_groups(work_id, limit=limit, offset=offset)
        )

        # Collect all chapter IDs to query translation status
        chapter_ids = []
        for item_type, data, _sort_key in items:
            if item_type == "chapter":
                chapter_ids.append(data.id)
            elif item_type == "group":
                for member in data.members:
                    chapter_ids.append(member.chapter_id)

        # Get completed translation statuses in one query
        completed_chapter_ids = _get_completed_translation_chapter_ids(db, chapter_ids)

        # Build response with mixed items
        response_items = []
        for item_type, data, sort_key in items:
            if item_type == "group":
                # data is a ChapterGroup
                group = data
                members_count = len(group.members)
                min_sort_key = float(sort_key)

                group_chapter_ids = [m.chapter_id for m in group.members]
                is_group_translated = len(group_chapter_ids) > 0 and all(
                    cid in completed_chapter_ids for cid in group_chapter_ids
                )

                response_items.append(
                    ChapterOrGroup(
                        item_type="group",
                        data=ChapterGroupOut(
                            id=group.id,
                            work_id=group.work_id,
                            name=group.name,
                            created_at=group.created_at,
                            updated_at=group.updated_at,
                            member_count=members_count,
                            min_sort_key=min_sort_key,
                            item_type="group",
                            is_fully_translated=is_group_translated,
                        ),
                    )
                )
            else:
                # data is a Chapter
                chapter_out = ChapterOut.model_validate(data)
                chapter_out.is_fully_translated = data.id in completed_chapter_ids
                response_items.append(ChapterOrGroup(item_type="chapter", data=chapter_out))

        return ChaptersWithGroupsResponse(
            items=response_items,
            total_chapters=total_chapters,
            total_groups=total_groups,
            total_items=total_items,  # Total number of items available (before pagination)
            offset=offset,
            limit=limit,
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

        next_chapter = chapters_service.get_next_chapter(work_id, chapter.sort_key)
        prev_chapter = chapters_service.get_previous_chapter(work_id, chapter.sort_key)

        response = ChapterDetailOut.model_validate(chapter)
        response.next_chapter_id = next_chapter.id if next_chapter else None
        response.prev_chapter_id = prev_chapter.id if prev_chapter else None
        return response


@router.post("/{work_id}/scrape-chapters", response_model=ChapterScrapeResponse)
def request_chapter_scrape(
    work_id: int,
    payload: ChapterScrapeRequest,
    background_tasks: BackgroundTasks,
):
    with SessionLocal() as db:
        works_service = WorksService(db)
        scrape_manager = ScrapeManager(db)

        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None

        # Check for existing job (and handle timeout logic)
        existing_job = scrape_manager.get_active_job(work_id)
        if existing_job:
            raise HTTPException(
                status_code=409, detail=f"Scrape already in progress (job {existing_job.id})"
            )

        # Create new job
        job = scrape_manager.create_job(
            work_id=work.id, start=Decimal(str(payload.start)), end=Decimal(str(payload.end))
        )

        # Start background task
        background_tasks.add_task(scrape_manager.run_scrape_job, job.id, force=payload.force)

        return ChapterScrapeResponse(
            work_id=work.id,
            start=payload.start,
            end=payload.end,
            force=payload.force,
            status="pending",
            job_id=job.id,
            requested=0,
            created=0,
            updated=0,
            skipped=0,
            errors=[],
        )


@router.post("/{work_id}/scrape-cancel")
def cancel_chapter_scrape(work_id: int):
    """Cancel an active scrape job."""
    with SessionLocal() as db:
        scrape_manager = ScrapeManager(db)

        # Check active job
        job = scrape_manager.get_active_job(work_id)
        if not job:
            return {"status": "no_active_job"}

        job.status = "cancelled"
        db.add(job)
        db.commit()

        return {"status": "cancelled", "job_id": job.id}


@router.get("/{work_id}/scrape-status")
async def stream_scrape_status(work_id: int, request: Request):
    """Stream scrape status events for a work."""
    # We don't use the DB session directly here for the generator context potentially
    # But checking if work exists is good practice

    # We'll rely on the manager to handle subscription
    # Note: Using ScrapeManager with a ephemeral session just for setup if needed

    async def event_generator():
        # Short-lived session to check work existence/current status
        db = SessionLocal()
        scrape_manager = ScrapeManager(db)

        try:
            # Check active job to send initial state
            job = scrape_manager.get_active_job(work_id)
            if not job:
                job = scrape_manager.get_latest_job(work_id)

            if job:
                yield _sse_event(
                    "job-status",
                    {
                        "status": job.status,
                        "progress": job.progress,
                        "total": job.total,
                        "created": job.created_count,
                        "updated": job.updated_count,
                        "skipped": job.skipped_count,
                        "failed": job.failed_count,
                        "errors": job.error_details or [],
                    },
                )
            else:
                yield _sse_event("job-status", {"status": "idle"})
        finally:
            db.close()

        # Subscribe to broadcast (_subscribers is module-global, any instance works)

        db_sub = SessionLocal()
        manager = ScrapeManager(db_sub)
        try:
            async for event in manager.subscribe(work_id):
                if await request.is_disconnected():
                    break
                yield _sse_event(event["event"], event["data"])
        finally:
            db_sub.close()

    return EventSourceResponse(event_generator())


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


@router.patch(
    "/{work_id}/chapters/{chapter_id}/segments/batch",
    response_model=ChapterTranslationStateOut,
)
def batch_update_segments(work_id: int, chapter_id: int, payload: BatchSegmentUpdateRequest):
    """Apply manual edits to multiple translation segments.

    Updates the target translation text for each specified segment.
    Clears any cached explanations for edited segments since the
    translation text has changed.
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

        translation = translation_service.get_or_create_translation(chapter.id)

        edits = [{"segment_id": e.segment_id, "tgt": e.tgt} for e in payload.edits]
        translation_service.batch_update_segment_translations(translation.id, edits)

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

        expires_at = datetime.fromtimestamp(token.expires_at, tz=UTC)
        return ChapterPromptOverrideResponse(token=token.token, expires_at=expires_at)


def _sse_event(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}



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


def _translation_event_to_sse(event: TranslationEvent) -> dict:
    match event:
        case TranslationStatusEvent():
            return _sse_event(
                "translation-status",
                {"chapter_translation_id": event.chapter_translation_id, "status": event.status},
            )
        case SegmentStartEvent():
            return _sse_event(
                "segment-start",
                {
                    "chapter_translation_id": event.chapter_translation_id,
                    "segment_id": event.segment_id,
                    "order_index": event.order_index,
                    "start": event.start,
                    "end": event.end,
                    "src": event.src,
                },
            )
        case SegmentDeltaEvent():
            return _sse_event(
                "segment-delta",
                {
                    "chapter_translation_id": event.chapter_translation_id,
                    "segment_id": event.segment_id,
                    "order_index": event.order_index,
                    "delta": event.delta,
                },
            )
        case SegmentCompleteEvent():
            return _sse_event(
                "segment-complete",
                {
                    "chapter_translation_id": event.chapter_translation_id,
                    "segment_id": event.segment_id,
                    "order_index": event.order_index,
                    "text": event.text,
                },
            )
        case TranslationCompleteEvent():
            return _sse_event(
                "translation-complete",
                {"chapter_translation_id": event.chapter_translation_id, "status": event.status},
            )
        case TranslationErrorEvent():
            payload: dict = {
                "chapter_translation_id": event.chapter_translation_id,
                "error": event.error,
            }
            if event.segment_id is not None:
                payload["segment_id"] = event.segment_id
            if event.order_index is not None:
                payload["order_index"] = event.order_index
            return _sse_event("translation-error", payload)


def _explanation_event_to_sse(event: ExplanationEvent) -> dict:
    match event:
        case ExplanationDeltaEvent():
            return _sse_event(
                "explanation-delta", {"segment_id": event.segment_id, "delta": event.delta}
            )
        case ExplanationCompleteEvent():
            return _sse_event(
                "explanation-complete",
                {"segment_id": event.segment_id, "explanation": event.explanation},
            )
        case ExplanationErrorEvent():
            return _sse_event(
                "explanation-error", {"segment_id": event.segment_id, "error": event.error}
            )


@router.get("/{work_id}/chapters/{chapter_id}/translate/stream")
async def stream_chapter_translation(
    work_id: int,
    chapter_id: int,
    request: Request,
    prompt_override_token: str | None = Query(default=None),
):
    # TODO: Gate concurrent translators per chapter translation.
    # TODO: Handle reset invalidating in-flight segments.
    db = SessionLocal()
    try:
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

        prompt_override = _resolve_prompt_override(prompt_override_token, work_id, chapter_id)
        workflow = TranslationWorkflow(db)

        async def event_generator():
            try:
                async for event in workflow.start_or_resume(
                    chapter,
                    work_id,
                    prompt_override=prompt_override,
                    is_disconnected=request.is_disconnected,
                ):
                    yield _translation_event_to_sse(event)
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
    instruction: str | None = Query(default=None, max_length=2000),
):
    """Retranslate a single segment in a chapter translation.

    Args:
        instruction: Optional user instruction to guide the retranslation
            (e.g., "make it more casual", "keep the honorific").
    """
    db = SessionLocal()
    try:
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

        prompt_override = _resolve_prompt_override(prompt_override_token, work_id, chapter_id)
        workflow = TranslationWorkflow(db)

        try:
            workflow.preflight_segment_check(chapter, segment_id)
        except SegmentNotFoundError:
            db.close()
            raise HTTPException(status_code=404, detail="segment not found") from None

        async def event_generator():
            try:
                async for event in workflow.retranslate_segment(
                    chapter,
                    segment_id,
                    work_id,
                    prompt_override=prompt_override,
                    instruction=instruction,
                    is_disconnected=request.is_disconnected,
                ):
                    yield _translation_event_to_sse(event)
            finally:
                db.close()

        return EventSourceResponse(event_generator())
    except Exception:
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
    db = SessionLocal()
    try:
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

        workflow = ExplanationWorkflow(db)
        try:
            workflow.preflight_check(chapter, segment_id)
        except SegmentNotFoundError:
            db.close()
            raise HTTPException(status_code=404, detail="segment not found") from None
        except SegmentNotTranslatedError:
            db.close()
            raise HTTPException(status_code=400, detail="segment is not translated") from None

        async def event_generator():
            try:
                async for event in workflow.explain_segment(
                    chapter,
                    segment_id,
                    force=False,
                    is_disconnected=request.is_disconnected,
                ):
                    yield _explanation_event_to_sse(event)
            finally:
                db.close()

        return EventSourceResponse(event_generator())
    except HTTPException:
        raise
    except Exception:
        db.close()
        raise


@router.post("/{work_id}/chapters/{chapter_id}/segments/{segment_id}/regenerate-explanation")
async def regenerate_explanation(
    work_id: int,
    chapter_id: int,
    segment_id: int,
    request: Request,
):
    """Clear and regenerate explanation for a translation segment."""
    db = SessionLocal()
    try:
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

        workflow = ExplanationWorkflow(db)
        try:
            workflow.preflight_check(chapter, segment_id)
        except SegmentNotFoundError:
            db.close()
            raise HTTPException(status_code=404, detail="segment not found") from None
        except SegmentNotTranslatedError:
            db.close()
            raise HTTPException(status_code=400, detail="segment is not translated") from None

        async def event_generator():
            try:
                async for event in workflow.explain_segment(
                    chapter,
                    segment_id,
                    force=True,
                    is_disconnected=request.is_disconnected,
                ):
                    yield _explanation_event_to_sse(event)
            finally:
                db.close()

        return EventSourceResponse(event_generator())
    except HTTPException:
        raise
    except Exception:
        db.close()
        raise
