from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models import ScrapeJob, Work
from services.scrape_manager import ScrapeManager
from tests.test_chapters_service import _attach_fake_scraper


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
