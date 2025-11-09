from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Work
from .exceptions import WorkNotFoundError
from .utils import sanitize_pagination


class WorksService:
    """Encapsulates queries and validation for Work entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self, q: str | None, limit: int, offset: int, max_limit: int = 100
    ) -> Tuple[List[Work], int, int, int]:
        limit, offset = sanitize_pagination(limit, offset, max_limit=max_limit)

        stmt = select(Work)
        count_stmt = select(func.count()).select_from(Work)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(Work.title).like(like))
            count_stmt = count_stmt.where(func.lower(Work.title).like(like))

        stmt = stmt.order_by(Work.title.asc(), Work.id.asc()).limit(limit).offset(offset)
        rows = self.session.execute(stmt).scalars().all()
        total = self.session.execute(count_stmt).scalar_one()
        return rows, total, limit, offset

    def get_work(self, work_id: int) -> Work:
        work = self.session.get(Work, work_id)
        if not work:
            raise WorkNotFoundError(f"work {work_id} not found")
        return work
