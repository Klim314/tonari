from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Dict, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Chapter, Work
from app.scrapers import scraper_registry
from app.scrapers.exceptions import ScraperError, ScraperNotFoundError

from .exceptions import ChapterNotFoundError, ChapterScrapeError
from .utils import sanitize_pagination

SORT_KEY_STEP = Decimal("0.0001")


@dataclass(slots=True)
class ChapterScrapeErrorEntry:
    chapter: Decimal
    reason: str


@dataclass(slots=True)
class ChapterScrapeSummary:
    work_id: int
    start: Decimal
    end: Decimal
    force: bool
    requested: int
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[ChapterScrapeErrorEntry] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.requested == 0:
            return "noop"
        if self.errors:
            if self.created == 0 and self.updated == 0 and self.skipped == 0:
                return "failed"
            return "partial"
        return "completed"

    def add_error(self, chapter: Decimal, reason: str) -> None:
        self.errors.append(ChapterScrapeErrorEntry(chapter=chapter, reason=reason))


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
            .order_by(Chapter.sort_key.asc(), Chapter.idx.asc(), Chapter.id.asc())
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

    def get_next_chapter(self, work_id: int, current_sort_key: Decimal) -> Chapter | None:
        stmt = (
            select(Chapter)
            .where(
                Chapter.work_id == work_id,
                Chapter.sort_key > current_sort_key,
            )
            .order_by(Chapter.sort_key.asc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def get_previous_chapter(self, work_id: int, current_sort_key: Decimal) -> Chapter | None:
        stmt = (
            select(Chapter)
            .where(
                Chapter.work_id == work_id,
                Chapter.sort_key < current_sort_key,
            )
            .order_by(Chapter.sort_key.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def scrape_work_for_chapters(
        self,
        work: Work,
        start: Decimal | float | int,
        end: Decimal | float | int,
        *,
        force: bool = False,
    ) -> ChapterScrapeSummary:
        if not work.source or not work.source_id:
            raise ChapterScrapeError("work is missing source identifier")

        start_key = self._normalize_sort_key(start)
        end_key = self._normalize_sort_key(end)
        if end_key < start_key:
            raise ChapterScrapeError("end must be greater than or equal to start")

        scraper = scraper_registry.resolve_by_source(work.source)
        sort_keys = self._expand_sort_keys(start_key, end_key)
        summary = ChapterScrapeSummary(
            work_id=work.id,
            start=start_key,
            end=end_key,
            force=force,
            requested=len(sort_keys),
        )

        existing = self._load_existing_chapters(work.id, sort_keys)

        for sort_key in sort_keys:
            try:
                chapter_url = scraper.build_chapter_url(work.source_id, sort_key)
                title, normalized_text = scraper.scrape_chapter(chapter_url)
            except ScraperError as exc:
                summary.add_error(sort_key, str(exc))
                continue
            except ScraperNotFoundError as exc:
                summary.add_error(sort_key, str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                summary.add_error(sort_key, f"unexpected error: {exc}")
                continue

            text_hash = self._hash_text(normalized_text)
            existing_chapter = existing.get(sort_key)
            idx = self._idx_from_sort_key(sort_key)
            if existing_chapter is None:
                chapter = Chapter(
                    work_id=work.id,
                    idx=idx,
                    sort_key=sort_key,
                    title=title,
                    normalized_text=normalized_text,
                    text_hash=text_hash,
                )
                self.session.add(chapter)
                summary.created += 1
            else:
                if not force and existing_chapter.text_hash == text_hash:
                    summary.skipped += 1
                    continue
                existing_chapter.idx = idx
                existing_chapter.sort_key = sort_key
                existing_chapter.title = title
                existing_chapter.normalized_text = normalized_text
                existing_chapter.text_hash = text_hash
                summary.updated += 1

        self.session.commit()
        return summary

    def _load_existing_chapters(
        self, work_id: int, sort_keys: List[Decimal]
    ) -> Dict[Decimal, Chapter]:
        if not sort_keys:
            return {}
        stmt = select(Chapter).where(
            Chapter.work_id == work_id,
            Chapter.sort_key.in_(sort_keys),
        )
        rows = self.session.execute(stmt).scalars().all()
        return {self._normalize_sort_key(row.sort_key): row for row in rows}

    def _expand_sort_keys(self, start: Decimal, end: Decimal) -> List[Decimal]:
        if start == end:
            return [start]

        keys: list[Decimal] = []
        cursor = start
        if self._has_fraction(start):
            keys.append(start)
            cursor = start.to_integral_value(rounding=ROUND_CEILING)
        else:
            cursor = start

        whole_end = end.to_integral_value(rounding=ROUND_FLOOR)
        while cursor <= whole_end:
            normalized_cursor = self._normalize_sort_key(cursor)
            if normalized_cursor >= start:
                keys.append(normalized_cursor)
            cursor += 1

        if self._has_fraction(end) and end not in keys:
            keys.append(end)

        keys = sorted(set(keys))
        return keys

    @staticmethod
    def _normalize_sort_key(value: Decimal | float | int) -> Decimal:
        if isinstance(value, Decimal):
            decimal_value = value
        else:
            decimal_value = Decimal(str(value))
        return decimal_value.quantize(SORT_KEY_STEP)

    @staticmethod
    def _has_fraction(value: Decimal) -> bool:
        return value != value.to_integral_value()

    @staticmethod
    def _idx_from_sort_key(sort_key: Decimal) -> int:
        integral = sort_key.to_integral_value(rounding=ROUND_FLOOR)
        return max(1, int(integral))

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
