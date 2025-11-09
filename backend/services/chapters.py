from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Chapter
from .exceptions import ChapterNotFoundError
from .utils import sanitize_pagination


class ChaptersService:
    """Queries and helpers for chapters."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_chapters_for_work(
        self, work_id: int, limit: int, offset: int, max_limit: int = 100
    ) -> Tuple[List[Chapter], int, int, int]:
        limit, offset = sanitize_pagination(limit, offset, max_limit=max_limit)

        stmt = (
            select(Chapter)
            .where(Chapter.work_id == work_id)
            .order_by(Chapter.idx.asc(), Chapter.id.asc())
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).select_from(Chapter).where(Chapter.work_id == work_id)
        rows = self.session.execute(stmt).scalars().all()
        total = self.session.execute(count_stmt).scalar_one()
        return rows, total, limit, offset

    def get_chapter(self, chapter_id: int) -> Chapter:
        chapter = self.session.get(Chapter, chapter_id)
        if not chapter:
            raise ChapterNotFoundError(f"chapter {chapter_id} not found")
        return chapter
