from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import AsyncGenerator, Dict, Tuple

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ScrapeJob, Work
from app.scrapers import scraper_registry
from app.scrapers.exceptions import ScraperError, ScraperNotFoundError
from services.chapters import ChaptersService, ChapterScrapeSummary

logger = logging.getLogger(__name__)

# In-memory broadcaster for SSE
# Map: work_id -> list of queues
_subscribers: Dict[int, list[asyncio.Queue]] = {}


class ScrapeManager:
    """Manages background scrape jobs and real-time updates."""

    def __init__(self, db: Session):
        self.db = db
        self.chapters_service = ChaptersService(db)

    def create_job(self, work_id: int, start: Decimal, end: Decimal) -> ScrapeJob:
        """Create a new scrape job record."""
        job = ScrapeJob(
            work_id=work_id,
            start=start,
            end=end,
            status="pending",
            progress=0,
            total=0,  # Unknown initially
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_active_job(self, work_id: int) -> ScrapeJob | None:
        """Return an active job if one exists and is not stale."""
        stmt = select(ScrapeJob).where(
            ScrapeJob.work_id == work_id,
            ScrapeJob.status.in_(["pending", "running"]),
        )
        job = self.db.execute(stmt).scalars().first()
        
        if not job:
            return None

        # Check for timeout (2 minutes since last update)
        # Assuming updated_at is timezone aware or UTC
        now = datetime.now(timezone.utc)
        # Ensure updated_at has timezone info for comparison, assuming DB stores as generic timestamp
        last_update = job.updated_at
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
            
        if now - last_update > timedelta(minutes=2):
            logger.warning(f"Marking stale scrape job {job.id} as failed (timeout)")
            job.status = "failed"
            self.db.add(job)
            self.db.commit()
            return None
            
        return job

    async def run_scrape_job(self, job_id: int, force: bool = False):
        """
        Main async loop for scraping.
        """
        # We need a new session for the background task
        with SessionLocal() as db:
            job = db.get(ScrapeJob, job_id)
            if not job:
                logger.error(f"Scrape job {job_id} not found")
                return

            try:
                job.status = "running"
                db.commit()
                await self._broadcast(job.work_id, "job-status", {"status": "running"})

                # Fetch work
                work = db.get(Work, job.work_id)
                if not work:
                    raise Exception("Work not found")

                chapters_service = ChaptersService(db)
                
                # Validation logic duplicated/borrowed from ChaptersService to setup the loop
                if not work.source or not work.source_id:
                    raise Exception("Work missing source info")

                start_key = chapters_service._normalize_sort_key(job.start)
                end_key = chapters_service._normalize_sort_key(job.end)
                
                # Expand specific keys to scrape
                keys_to_scrape = chapters_service._expand_sort_keys(start_key, end_key)
                job.total = len(keys_to_scrape)
                db.commit()

                scraper = scraper_registry.resolve_by_source(work.source)
                
                completed_count = 0
                
                for i, sort_key in enumerate(keys_to_scrape):
                    # Check for cancellation/freshness
                    db.refresh(job)
                    if job.status not in ["running", "pending"]:
                        logger.info(f"Job {job.id} cancelled or usurped")
                        return

                    # Update heartbeat
                    job.updated_at = datetime.now(timezone.utc)
                    job.progress = i
                    db.commit()

                    try:
                        # Scrape Logic
                        chapter_url = scraper.build_chapter_url(work.source_id, sort_key)
                        
                        # Run synchronous scrape in threadpool to avoid blocking event loop
                        title, normalized_text = await run_in_threadpool(scraper.scrape_chapter, chapter_url)
                        
                        # Verify we can persist
                        db.refresh(work) # Ensure work attached
                        
                        # Using internal helper to save chapter - we might want to expose this on service
                        # For now, we'll manually invoke the logic from chapters service or replicate it slightly
                        # Replicating slightly for granular control (or we could make `save_chapter` public)
                        
                        text_hash = chapters_service._hash_text(normalized_text)
                        
                        # Check existing
                        existing = chapters_service._load_existing_chapters(work.id, [sort_key])
                        existing_chapter = existing.get(sort_key)
                        idx = chapters_service._idx_from_sort_key(sort_key)

                        if existing_chapter:
                             if force or existing_chapter.text_hash != text_hash:
                                existing_chapter.idx = idx
                                existing_chapter.sort_key = sort_key
                                existing_chapter.title = title
                                existing_chapter.normalized_text = normalized_text
                                existing_chapter.text_hash = text_hash
                                db.add(existing_chapter)
                                await self._broadcast(job.work_id, "chapter-found", {
                                    "idx": float(sort_key), 
                                    "title": title,
                                    "status": "updated"
                                })
                        else:
                            # Create new
                            from app.models import Chapter
                            new_chapter = Chapter(
                                work_id=work.id,
                                idx=idx,
                                sort_key=sort_key,
                                title=title,
                                normalized_text=normalized_text,
                                text_hash=text_hash,
                            )
                            db.add(new_chapter)
                            await self._broadcast(job.work_id, "chapter-found", {
                                "idx": float(sort_key), 
                                "title": title,
                                "status": "created"
                            })
                        
                        db.commit()
                        completed_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error scraping chapter {sort_key}: {e}")
                        # We continue to next chapter
                        pass

                # Done
                job.status = "completed"
                job.progress = job.total
                db.commit()
                await self._broadcast(job.work_id, "job-status", {"status": "completed"})

            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
                job.status = "failed"
                # TODO: Store error reason
                db.commit()
                await self._broadcast(job.work_id, "job-status", {"status": "failed", "error": str(e)})


    async def subscribe(self, work_id: int) -> AsyncGenerator[dict, None]:
        """Subscribe to SSE events for a work."""
        queue = asyncio.Queue()
        if work_id not in _subscribers:
            _subscribers[work_id] = []
        _subscribers[work_id].append(queue)

        try:
            while True:
                msg = await queue.get()
                yield msg
        finally:
            if work_id in _subscribers:
                if queue in _subscribers[work_id]:
                    _subscribers[work_id].remove(queue)
                if not _subscribers[work_id]:
                    del _subscribers[work_id]

    async def _broadcast(self, work_id: int, event_type: str, data: dict):
        """Push event to all subscribers."""
        if work_id in _subscribers:
            msg = {"event": event_type, "data": data} # sse-starlette format handles json dumps often, but we'll do it cleanly
            for q in _subscribers[work_id]:
                await q.put(msg)

