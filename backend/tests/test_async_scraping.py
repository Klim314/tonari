from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from app.models import Chapter, ScrapeJob, Work
from services.scrape_manager import ScrapeManager
from tests.test_chapters_service import FakeScraper, _attach_fake_scraper


def test_create_scrape_job(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Test Job Work", source="fake", source_id="job-1")
    db_session.add(work)
    db_session.commit()

    manager = ScrapeManager(db_session)
    job = manager.create_job(work.id, Decimal("1"), Decimal("10"))

    assert job.id is not None
    assert job.status == "pending"
    assert job.work_id == work.id
    assert job.progress == 0
    assert job.total == 10


def test_get_active_scrape_job(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Active Job Work", source="fake", source_id="job-2")
    db_session.add(work)
    db_session.commit()

    manager = ScrapeManager(db_session)

    # No job initially
    assert manager.get_active_job(work.id) is None

    # Create active job
    job = manager.create_job(work.id, Decimal("1"), Decimal("10"))
    active = manager.get_active_job(work.id)
    assert active is not None
    assert active.id == job.id

    # Mark as completed
    job.status = "completed"
    db_session.add(job)
    db_session.commit()

    assert manager.get_active_job(work.id) is None


def test_get_active_job_marks_stale_jobs_failed(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Stale Job Work", source="fake", source_id="job-stale")
    db_session.add(work)
    db_session.commit()

    stale_job = ScrapeJob(
        work_id=work.id,
        start=Decimal("1"),
        end=Decimal("2"),
        status="running",
        progress=1,
        total=2,
        updated_at=datetime.now(UTC) - timedelta(minutes=3),
    )
    db_session.add(stale_job)
    db_session.commit()

    manager = ScrapeManager(db_session)

    assert manager.get_active_job(work.id) is None
    db_session.refresh(stale_job)
    assert stale_job.status == "failed"


def test_run_scrape_job_updates_job_progress(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Progress Work", source="fake", source_id="job-3")
    db_session.add(work)
    db_session.commit()

    manager = ScrapeManager(db_session)
    job = manager.create_job(work.id, Decimal("1"), Decimal("5"))

    asyncio.run(manager.run_scrape_job(job.id, force=False))

    db_session.refresh(job)

    assert job.status == "completed"
    assert job.total == 5
    assert job.progress == 5


def test_api_concurrency_prevention(client, db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)

    # Create work via DB directly
    work = Work(title="API Concurrency Work", source="fake", source_id="job-4")
    db_session.add(work)
    db_session.commit()
    work_id = work.id

    # 1. Start a scrape (mocking the background task to not actually run immediately/finish instantly)
    # We want to verified the endpoint creates a job.

    # However, the endpoint automatically adds a background task.
    # In TestClient, background tasks run after the response.

    # We can pre-seed a job in the DB to simulate "Job is running"
    manager = ScrapeManager(db_session)
    existing_job = manager.create_job(work_id, Decimal("1"), Decimal("10"))
    existing_job.status = "running"
    db_session.commit()

    # 2. Call endpoint
    resp = client.post(
        f"/works/{work_id}/scrape-chapters", json={"start": 5, "end": 15, "force": True}
    )

    assert resp.status_code == 409
    assert f"job {existing_job.id}" in resp.json()["detail"]


def test_run_scrape_job_tracks_counters_on_clean_run(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Counter Work", source="fake", source_id="job-counters")
    db_session.add(work)
    db_session.commit()

    manager = ScrapeManager(db_session)
    job = manager.create_job(work.id, Decimal("1"), Decimal("5"))

    asyncio.run(manager.run_scrape_job(job.id, force=False))

    db_session.refresh(job)
    assert job.status == "completed"
    assert job.created_count == 5
    assert job.updated_count == 0
    assert job.skipped_count == 0
    assert job.failed_count == 0
    assert job.error_details is None


def test_run_scrape_job_marks_partial_when_some_chapters_fail(db_session, monkeypatch):
    class PartialFakeScraper(FakeScraper):
        def scrape_chapter(self, url: str) -> tuple[str, str]:
            if url.endswith("/3.0000"):
                raise ValueError("simulated scrape error for ch 3")
            return super().scrape_chapter(url)

    monkeypatch.setattr("app.scrapers.scraper_registry._scrapers", [PartialFakeScraper()])

    work = Work(title="Partial Work", source="fake", source_id="job-partial")
    db_session.add(work)
    db_session.commit()

    manager = ScrapeManager(db_session)
    job = manager.create_job(work.id, Decimal("1"), Decimal("5"))

    asyncio.run(manager.run_scrape_job(job.id, force=False))

    db_session.refresh(job)
    assert job.status == "partial"
    assert job.failed_count == 1
    assert job.created_count == 4
    assert job.error_details is not None
    assert len(job.error_details) == 1
    assert job.error_details[0]["chapter"] == 3.0
    assert "simulated scrape error" in job.error_details[0]["reason"]


def test_run_scrape_job_marks_failed_when_all_chapters_fail(db_session, monkeypatch):
    class AlwaysFailScraper(FakeScraper):
        def scrape_chapter(self, url: str) -> tuple[str, str]:
            raise RuntimeError("always fails")

    monkeypatch.setattr("app.scrapers.scraper_registry._scrapers", [AlwaysFailScraper()])

    work = Work(title="All Fail Work", source="fake", source_id="job-allfail")
    db_session.add(work)
    db_session.commit()

    manager = ScrapeManager(db_session)
    job = manager.create_job(work.id, Decimal("1"), Decimal("3"))

    asyncio.run(manager.run_scrape_job(job.id, force=False))

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.failed_count == 3
    assert job.created_count == 0
    assert job.error_details is not None
    assert len(job.error_details) == 3


def test_run_scrape_job_tracks_updated_and_skipped(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Update Skip Work", source="fake", source_id="job-upskip")
    db_session.add(work)
    db_session.commit()

    from services.chapters import ChaptersService

    chapters_service = ChaptersService(db_session)

    # Seed ch 1 with correct hash (will be skipped) and ch 2 with wrong hash (will be updated)
    fake_title_1, fake_text_1 = "Chapter 1", "Body 1"
    fake_title_2, fake_text_2 = "Chapter 2", "Body 2"
    correct_hash = chapters_service._hash_text(fake_text_1)
    stale_hash = "deadbeef" * 8  # wrong hash → triggers update

    ch1 = Chapter(
        work_id=work.id,
        idx=1,
        sort_key=Decimal("1.0000"),
        title=fake_title_1,
        normalized_text=fake_text_1,
        text_hash=correct_hash,
    )
    ch2 = Chapter(
        work_id=work.id,
        idx=2,
        sort_key=Decimal("2.0000"),
        title=fake_title_2,
        normalized_text=fake_text_2,
        text_hash=stale_hash,
    )
    db_session.add_all([ch1, ch2])
    db_session.commit()

    manager = ScrapeManager(db_session)
    # Scrape range 1–3: ch1 skipped, ch2 updated, ch3 created
    job = manager.create_job(work.id, Decimal("1"), Decimal("3"))

    asyncio.run(manager.run_scrape_job(job.id, force=False))

    db_session.refresh(job)
    assert job.status == "completed"
    assert job.created_count == 1
    assert job.updated_count == 1
    assert job.skipped_count == 1
    assert job.failed_count == 0


def test_run_scrape_job_terminal_broadcast_includes_errors(db_session, monkeypatch):
    class PartialFakeScraper(FakeScraper):
        def scrape_chapter(self, url: str) -> tuple[str, str]:
            if url.endswith("/2.0000"):
                raise ValueError("broadcast test error")
            return super().scrape_chapter(url)

    monkeypatch.setattr("app.scrapers.scraper_registry._scrapers", [PartialFakeScraper()])

    work = Work(title="Broadcast Work", source="fake", source_id="job-broadcast")
    db_session.add(work)
    db_session.commit()

    broadcast_calls: list[tuple[int, str, dict]] = []

    async def capture_broadcast(work_id, event_type, data):
        broadcast_calls.append((work_id, event_type, data))

    manager = ScrapeManager(db_session)
    job = manager.create_job(work.id, Decimal("1"), Decimal("3"))

    with patch.object(manager, "_broadcast", side_effect=capture_broadcast):
        asyncio.run(manager.run_scrape_job(job.id, force=False))

    db_session.refresh(job)

    # Find the terminal job-status broadcast
    terminal = next(
        (
            d
            for (_, evt, d) in broadcast_calls
            if evt == "job-status"
            and d["status"] in ("partial", "failed", "completed")
            and "errors" in d
        ),
        None,
    )
    assert terminal is not None, "Expected a terminal job-status broadcast with errors key"
    assert terminal["status"] == "partial"
    assert len(terminal["errors"]) == 1
    assert terminal["errors"][0]["chapter"] == 2.0


def test_run_scrape_job_marks_job_failed_when_work_has_no_source(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Missing Source Work")
    db_session.add(work)
    db_session.commit()

    manager = ScrapeManager(db_session)
    job = manager.create_job(work.id, Decimal("1"), Decimal("2"))

    asyncio.run(manager.run_scrape_job(job.id, force=False))

    db_session.refresh(job)
    assert job.status == "failed"
