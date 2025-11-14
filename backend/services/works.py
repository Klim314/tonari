from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Work, WorkPrompt
from app.scrapers import scraper_registry
from app.scrapers.types import WorkMetadata

from .exceptions import PromptNotFoundError, WorkNotFoundError
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

    def get_or_scrape_work(self, url: str, *, force: bool = False) -> Work:
        scraper = scraper_registry.resolve(url)
        descriptor = scraper.parse_descriptor(url)
        work = self._find_by_source(descriptor.source, descriptor.source_id)
        if work and not force:
            return work

        metadata = scraper.fetch_work_metadata(descriptor)
        if work:
            self._apply_metadata(work, metadata)
        else:
            work = Work(title=metadata.title)
            self._apply_metadata(work, metadata)
            self.session.add(work)
        self.session.flush()
        self.session.commit()
        self.session.refresh(work)
        return work

    def _find_by_source(self, source: str, source_id: str) -> Work | None:
        stmt = select(Work).where(Work.source == source, Work.source_id == source_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def set_work_default_prompt(self, work_id: int, prompt_id: int) -> WorkPrompt:
        """Set or update the default prompt for a work.

        Args:
            work_id: The work ID
            prompt_id: The prompt ID to set as default

        Returns:
            WorkPrompt object

        Raises:
            WorkNotFoundError: If work not found
            PromptNotFoundError: If prompt not found
        """
        from app.models import Prompt

        # Verify work and prompt exist
        work = self.get_work(work_id)
        prompt = self.session.get(Prompt, prompt_id)
        if not prompt:
            raise PromptNotFoundError(f"prompt {prompt_id} not found")

        # Check if work already has a prompt assigned
        existing = self.session.execute(
            select(WorkPrompt).where(WorkPrompt.work_id == work_id)
        ).scalar_one_or_none()

        if existing:
            # Update existing assignment
            existing.prompt_id = prompt_id
            self.session.add(existing)
        else:
            # Create new assignment
            work_prompt = WorkPrompt(work_id=work_id, prompt_id=prompt_id, is_default=True)
            self.session.add(work_prompt)

        self.session.commit()
        # Re-fetch to ensure we have the updated object
        result = self.session.execute(
            select(WorkPrompt).where(WorkPrompt.work_id == work_id)
        ).scalar_one()
        return result

    @staticmethod
    def _apply_metadata(work: Work, metadata: WorkMetadata) -> None:
        work.title = metadata.title
        work.source = metadata.source
        work.source_id = metadata.source_id
        meta = dict(metadata.extra or {})
        if metadata.homepage_url:
            meta["homepage_url"] = metadata.homepage_url
        if metadata.author:
            meta["author"] = metadata.author
        if metadata.description:
            meta["description"] = metadata.description
        if metadata.thumbnail_url:
            meta["thumbnail_url"] = metadata.thumbnail_url
        work.source_meta = meta or None
