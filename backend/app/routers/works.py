from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.scrapers.exceptions import ScraperError, ScraperNotFoundError
from app.schemas import (
    ChapterDetailOut,
    ChapterOut,
    ChapterScrapeRequest,
    ChapterScrapeResponse,
    PaginatedChaptersOut,
    PaginatedWorksOut,
    WorkImportRequest,
    WorkOut,
)
from services.chapters import ChaptersService
from services.exceptions import ChapterNotFoundError, ChapterScrapeError, WorkNotFoundError
from services.works import WorksService

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
