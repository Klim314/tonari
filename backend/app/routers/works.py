from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.db import SessionLocal
from app.scrapers.exceptions import ScraperError, ScraperNotFoundError
from app.schemas import (
    ChapterDetailOut,
    ChapterOut,
    ChapterScrapeRequest,
    ChapterScrapeResponse,
    ChapterTranslationStateOut,
    TranslationSegmentOut,
    PaginatedChaptersOut,
    PaginatedWorksOut,
    WorkImportRequest,
    WorkOut,
)
from services.chapters import ChaptersService
from services.exceptions import ChapterNotFoundError, ChapterScrapeError, WorkNotFoundError
from services.translation_stream import TranslationStreamService
from services.works import WorksService
from app.translation_service import stream_lorem_translation

router = APIRouter()


@router.get("/", response_model=PaginatedWorksOut)
def search_works(q: str | None = Query(default=None), limit: int = 50, offset: int = 0):
    with SessionLocal() as db:  # type: Session
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
    with SessionLocal() as db:  # type: Session
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
    with SessionLocal() as db:  # type: Session
        works_service = WorksService(db)
        try:
            work = works_service.get_work(work_id)
        except WorkNotFoundError:
            raise HTTPException(status_code=404, detail="work not found") from None
        return WorkOut.model_validate(work)


@router.get("/{work_id}/chapters", response_model=PaginatedChaptersOut)
def list_chapters_for_work(work_id: int, limit: int = 50, offset: int = 0):
    with SessionLocal() as db:  # type: Session
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
    with SessionLocal() as db:  # type: Session
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
    with SessionLocal() as db:  # type: Session
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
            errors=[{"chapter": float(err.chapter), "reason": err.reason} for err in summary.errors],
        )


@router.get("/{work_id}/chapters/{chapter_id}/translation", response_model=ChapterTranslationStateOut)
def get_chapter_translation_state(work_id: int, chapter_id: int):
    with SessionLocal() as db:  # type: Session
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


def _sse_event(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


@router.get("/{work_id}/chapters/{chapter_id}/translate/stream")
async def stream_chapter_translation(work_id: int, chapter_id: int, request: Request):
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
        segments = translation_service.ensure_segments(translation, chapter.normalized_text)
        has_work = translation_service.first_pending_segment(segments) is not None

        if not has_work:
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

        async def event_generator():
            try:
                translation.status = "running"
                db.add(translation)
                db.commit()
                yield _sse_event(
                    "translation-status",
                    {"chapter_translation_id": translation.id, "status": translation.status},
                )

                while True:
                    segment_rows = translation_service.list_segments(translation.id)
                    current = translation_service.first_pending_segment(segment_rows)
                    if current is None:
                        translation.status = "completed"
                        db.add(translation)
                        db.commit()
                        yield _sse_event(
                            "translation-complete",
                            {"chapter_translation_id": translation.id, "status": translation.status},
                        )
                        break

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

                    collected = ""
                    async for delta in stream_lorem_translation(src):
                        if await request.is_disconnected():
                            raise asyncio.CancelledError
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

            except asyncio.CancelledError:
                translation.status = "idle"
                db.add(translation)
                db.commit()
                raise
            finally:
                db.close()

        return EventSourceResponse(event_generator())

    except Exception:
        db.close()
        raise
