from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Chapter, Work
from app.schemas import PaginatedWorksOut, PaginatedChaptersOut, WorkOut, ChapterOut

router = APIRouter()


def _sanitize_pagination(limit: int, offset: int, max_limit: int = 100) -> tuple[int, int]:
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return limit, offset


@router.get("/", response_model=PaginatedWorksOut)
def search_works(q: str | None = Query(default=None), limit: int = 50, offset: int = 0):
    limit, offset = _sanitize_pagination(limit, offset)
    with SessionLocal() as db:  # type: Session
        stmt = select(Work)
        count_stmt = select(func.count()).select_from(Work)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(Work.title).like(like))
            count_stmt = count_stmt.where(func.lower(Work.title).like(like))
        stmt = stmt.order_by(Work.title.asc(), Work.id.asc()).limit(limit).offset(offset)
        rows = db.execute(stmt).scalars().all()
        total = db.execute(count_stmt).scalar_one()
        return PaginatedWorksOut(
            items=[WorkOut.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get("/{work_id}", response_model=WorkOut)
def get_work(work_id: int):
    with SessionLocal() as db:  # type: Session
        work = db.get(Work, work_id)
        if not work:
            raise HTTPException(status_code=404, detail="work not found")
        return WorkOut.model_validate(work)


@router.get("/{work_id}/chapters", response_model=PaginatedChaptersOut)
def list_chapters_for_work(work_id: int, limit: int = 50, offset: int = 0):
    limit, offset = _sanitize_pagination(limit, offset)
    with SessionLocal() as db:  # type: Session
        work = db.get(Work, work_id)
        if not work:
            raise HTTPException(status_code=404, detail="work not found")

        stmt = (
            select(Chapter)
            .where(Chapter.work_id == work_id)
            .order_by(Chapter.idx.asc(), Chapter.id.asc())
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).select_from(Chapter).where(Chapter.work_id == work_id)
        rows = db.execute(stmt).scalars().all()
        total = db.execute(count_stmt).scalar_one()
        return PaginatedChaptersOut(
            items=[ChapterOut.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )
