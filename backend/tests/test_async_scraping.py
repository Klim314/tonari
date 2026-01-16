from __future__ import annotations

import threading
from decimal import Decimal
from unittest.mock import MagicMock
import time

import pytest
from sqlalchemy import select

from app.models import Chapter, Work, ScrapeJob
from services.chapters import ChaptersService
from tests.test_chapters_service import _attach_fake_scraper

def test_create_scrape_job(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Test Job Work", source="fake", source_id="job-1")
    db_session.add(work)
    db_session.commit()

    service = ChaptersService(db_session)
    job = service.create_scrape_job(work.id, Decimal("1"), Decimal("10"), force=False)
    
    assert job.id is not None
    assert job.status == "pending"
    assert job.work_id == work.id
    assert job.progress == 0
    assert job.total == 0

def test_get_active_scrape_job(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Active Job Work", source="fake", source_id="job-2")
    db_session.add(work)
    db_session.commit()

    service = ChaptersService(db_session)
    
    # No job initially
    assert service.get_active_scrape_job(work.id) is None

    # Create active job
    job = service.create_scrape_job(work.id, 1, 10, False)
    active = service.get_active_scrape_job(work.id)
    assert active is not None
    assert active.id == job.id

    # Mark as completed
    job.status = "completed"
    db_session.add(job)
    db_session.commit()
    
    assert service.get_active_scrape_job(work.id) is None

def test_scrape_updates_job_progress(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Progress Work", source="fake", source_id="job-3")
    db_session.add(work)
    db_session.commit()

    service = ChaptersService(db_session)
    job = service.create_scrape_job(work.id, 1, 5, False)
    
    # Run scrape with job_id
    summary = service.scrape_work_for_chapters(work, 1, 5, force=False, job_id=job.id)
    
    db_session.refresh(job)

    assert summary.created == 5
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
    # So we can't easily "pause" the background task to test concurrency strictly via client calls 
    # unless we mock the service method to hang.
    
    # Mock ChaptersService.scrape_work_for_chapters to just sleep
    original_scrape = ChaptersService.scrape_work_for_chapters
    
    def slow_scrape(*args, **kwargs):
        # We don't actually need to sleep if we just want to test if the job exists
        # But to test the API returning the EXISTING job, we need the first job to be 'pending'/'running'
        # when the second request hits.
        pass

    # We can pre-seed a job in the DB to simulate "Job is running"
    service = ChaptersService(db_session)
    existing_job = service.create_scrape_job(work_id, 1, 10, False)
    existing_job.status = "running"
    db_session.commit()
    
    # 2. Call endpoint
    resp = client.post(f"/works/{work_id}/scrape-chapters", json={
        "start": 5, "end": 15, "force": True
    })
    
    assert resp.status_code == 200
    data = resp.json()
    
    # Should return the EXISTING job, not a new one
    assert data["job_id"] == existing_job.id
    # The response range should match the EXISTING job, not the requested one 
    # (based on our logic: "if existing_job: return existing_job")
    # Existing job was created with 1-10. Request was 5-15.
    assert data["start"] == 1.0 
    assert data["end"] == 10.0
