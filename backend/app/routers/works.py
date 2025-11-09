from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas import PaginatedWorksOut, PaginatedChaptersOut, WorkOut, ChapterOut
from services.chapters import ChaptersService
from services.exceptions import WorkNotFoundError
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
        chapters_service = ChaptersService(db)
        rows, total, limit, offset = chapters_service.get_chapters_for_work(
            work_id, limit=limit, offset=offset
        )
        return PaginatedChaptersOut(
            items=[ChapterOut.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )
