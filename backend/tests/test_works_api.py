from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chapter, ChapterTranslation, ScrapeJob, TranslationSegment, Work
from app.syosetu.scraper import SyosetuScraper
from services.scrape_manager import ScrapeManager


def _create_work(
    session: Session,
    title: str,
    chapter_count: int = 0,
    source: str = "syosetu",
    source_id: str | None = None,
) -> Work:
    slug = source_id or title.lower().replace(" ", "-")
    work = Work(title=title, source=source, source_id=slug, source_meta={"source": "test"})
    session.add(work)
    session.flush()

    for i in range(chapter_count):
        chapter = Chapter(
            work_id=work.id,
            idx=i + 1,
            sort_key=Decimal(i + 1),
            title=f"{title} #{i+1}",
            normalized_text=f"chapter {i+1}",
            text_hash=f"{title}-{i+1}",
        )
        session.add(chapter)
    session.commit()
    session.refresh(work)
    return work


def test_search_works_pagination(client, db_session):
    _create_work(db_session, "Beta")
    _create_work(db_session, "Alpha")
    _create_work(db_session, "Gamma")

    resp = client.get("/works?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    titles = [item["title"] for item in data["items"]]
    assert titles == ["Alpha", "Beta"]

    resp_page2 = client.get("/works?limit=2&offset=2")
    assert resp_page2.status_code == 200
    data2 = resp_page2.json()
    assert data2["items"][0]["title"] == "Gamma"


def test_search_works_filter(client, db_session):
    _create_work(db_session, "Alpha Tales")
    _create_work(db_session, "Beta Story")

    resp = client.get("/works?q=alpha")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Alpha Tales"


def test_list_chapters_for_work(client, db_session):
    work = _create_work(db_session, "Chronicles", chapter_count=3)

    resp = client.get(f"/works/{work.id}/chapters?limit=2")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_chapters"] == 3
    assert payload["total_groups"] == 0
    assert payload["total_items"] == 3
    # Items now have item_type and data fields
    assert payload["items"][0]["item_type"] == "chapter"
    assert payload["items"][0]["data"]["title"] == "Chronicles #1"
    assert payload["items"][1]["data"]["idx"] == 2

    resp2 = client.get(f"/works/{work.id}/chapters?offset=2")
    assert resp2.status_code == 200
    payload2 = resp2.json()
    assert len(payload2["items"]) == 1
    assert payload2["items"][0]["data"]["idx"] == 3


def test_list_chapters_for_missing_work(client):
    resp = client.get("/works/999/chapters")
    assert resp.status_code == 404


def test_get_work(client, db_session):
    work = _create_work(db_session, "Solo Work")
    resp = client.get(f"/works/{work.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Solo Work"

    missing = client.get("/works/999")
    assert missing.status_code == 404


def test_scrape_chapters_request(client, db_session, monkeypatch):
    def fake_scrape(self, url: str):
        chapter = url.rstrip("/").split("/")[-1]
        return f"Title {chapter}", f"Body {chapter}"

    monkeypatch.setattr(SyosetuScraper, "scrape_chapter", fake_scrape)

    work = _create_work(db_session, "Queued Work")
    resp = client.post(
        f"/works/{work.id}/scrape-chapters",
        json={"start": 1, "end": 3, "force": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["work_id"] == work.id
    assert data["force"] is True
    assert data["start"] == 1.0
    assert data["end"] == 3.0
    assert data["requested"] == 0
    assert data["created"] == 0
    assert data["updated"] == 0
    assert data["skipped"] == 0
    assert data["errors"] == []
    assert data["job_id"] is not None

    rows = db_session.execute(select(Chapter).where(Chapter.work_id == work.id)).scalars().all()
    assert len(rows) == 3

    job = db_session.get(ScrapeJob, data["job_id"])
    assert job is not None
    assert job.work_id == work.id


def test_scrape_chapters_missing_work(client):
    resp = client.post("/works/999/scrape-chapters", json={"start": 1, "end": 2})
    assert resp.status_code == 404


def test_scrape_chapters_without_source_fails_async_job(client, db_session):
    work = Work(title="Loose Work")
    db_session.add(work)
    db_session.commit()

    resp = client.post(f"/works/{work.id}/scrape-chapters", json={"start": 1, "end": 2})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "pending"
    assert payload["job_id"] is not None

    job = db_session.get(ScrapeJob, payload["job_id"])
    assert job is not None
    assert job.status == "failed"


def test_scrape_status_stream_starts_with_idle_state(client, monkeypatch):
    async def no_events(self, work_id: int):
        if False:
            yield {"event": "job-status", "data": {"status": "running"}}
        return

    monkeypatch.setattr(ScrapeManager, "subscribe", no_events)

    response = client.get("/works/123/scrape-status")

    assert response.status_code == 200
    assert "event: job-status" in response.text
    assert '{"status": "idle"}' in response.text


def test_scrape_status_stream_emits_active_job_state(client, db_session, monkeypatch):
    work = _create_work(db_session, "Streaming Work")
    manager = ScrapeManager(db_session)
    manager.create_job(work.id, Decimal("1"), Decimal("2"))

    async def no_events(self, work_id: int):
        if False:
            yield {"event": "job-status", "data": {"status": "running"}}
        return

    monkeypatch.setattr(ScrapeManager, "subscribe", no_events)

    response = client.get(f"/works/{work.id}/scrape-status")

    assert response.status_code == 200
    assert "event: job-status" in response.text
    assert '"status": "pending"' in response.text
    assert '"progress": 0' in response.text
    assert '"total": 2' in response.text


def test_scrape_status_stream_emits_latest_completed_job_state(client, db_session, monkeypatch):
    work = _create_work(db_session, "Completed Streaming Work")
    manager = ScrapeManager(db_session)
    job = manager.create_job(work.id, Decimal("1"), Decimal("2"))
    job.status = "completed"
    job.progress = 2
    db_session.add(job)
    db_session.commit()

    async def no_events(self, work_id: int):
        if False:
            yield {"event": "job-status", "data": {"status": "running"}}
        return

    monkeypatch.setattr(ScrapeManager, "subscribe", no_events)

    response = client.get(f"/works/{work.id}/scrape-status")

    assert response.status_code == 200
    assert "event: job-status" in response.text
    assert '"status": "completed"' in response.text
    assert '"progress": 2' in response.text
    assert '"total": 2' in response.text


def test_scrape_status_stream_forwards_broadcast_events(client, monkeypatch):
    async def fake_subscribe(self, work_id: int):
        yield {"event": "job-status", "data": {"status": "running", "progress": 1, "total": 3}}
        yield {"event": "chapter-found", "data": {"idx": 1.0, "title": "Chapter 1"}}

    monkeypatch.setattr(ScrapeManager, "get_active_job", lambda self, work_id: None)
    monkeypatch.setattr(ScrapeManager, "subscribe", fake_subscribe)

    response = client.get("/works/456/scrape-status")
    body = response.text

    assert response.status_code == 200
    assert body.count("event: job-status") >= 1
    assert body.count("event: chapter-found") == 1
    assert json.dumps({"status": "running", "progress": 1, "total": 3}) in body
    assert json.dumps({"idx": 1.0, "title": "Chapter 1"}) in body


def test_get_chapter_detail(client, db_session):
    work = _create_work(db_session, "Detail Work", chapter_count=1)
    chapter = (
        db_session.execute(select(Chapter).where(Chapter.work_id == work.id)).scalars().first()
    )
    resp = client.get(f"/works/{work.id}/chapters/{chapter.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == chapter.id
    assert payload["normalized_text"] == "chapter 1"


def test_get_chapter_detail_wrong_work(client, db_session):
    first = _create_work(db_session, "First", chapter_count=1)
    second = _create_work(db_session, "Second")
    chapter = (
        db_session.execute(select(Chapter).where(Chapter.work_id == first.id)).scalars().first()
    )
    resp = client.get(f"/works/{second.id}/chapters/{chapter.id}")
    assert resp.status_code == 404


def _parse_sse_events(text: str) -> list[tuple[str, dict]]:
    """Parse an SSE stream into a list of (event_name, data) tuples."""
    import json

    events = []
    current_event = None
    current_data = None
    for line in text.splitlines():
        if line.startswith("event: "):
            current_event = line[len("event: ") :]
        elif line.startswith("data: "):
            current_data = line[len("data: ") :]
        elif line == "" and current_event is not None and current_data is not None:
            events.append((current_event, json.loads(current_data)))
            current_event = None
            current_data = None
    return events


def test_stream_chapter_translation_persists_segments(client, db_session):
    work = _create_work(db_session, "Translated Work")
    chapter = Chapter(
        work_id=work.id,
        idx=1,
        sort_key=Decimal(1),
        title="Translated Work #1",
        normalized_text="彼は歩く。\n彼女も歩く。\n\n場面転換。",
        text_hash="translated-work-1",
    )
    db_session.add(chapter)
    db_session.commit()
    db_session.refresh(chapter)

    response = client.get(f"/works/{work.id}/chapters/{chapter.id}/translate/stream")

    assert response.status_code == 200

    events = _parse_sse_events(response.text)
    event_names = [name for name, _ in events]

    # Full event sequence: status(running) → [start/delta(s)/complete per segment] → complete
    assert event_names[0] == "translation-status"
    assert events[0][1]["status"] == "running"

    # Two translatable segments ("彼は歩く。\n彼女も歩く。" and "場面転換。"); whitespace skipped
    start_indices = [i for i, name in enumerate(event_names) if name == "segment-start"]
    assert len(start_indices) == 2

    for start_idx in start_indices:
        segment_id = events[start_idx][1]["segment_id"]
        # At least one delta follows
        next_names = event_names[start_idx + 1 :]
        assert "segment-delta" in next_names, "Expected segment-delta after segment-start"
        # segment-complete for this segment follows
        complete_for_seg = [
            i
            for i, (name, data) in enumerate(events)
            if name == "segment-complete" and data.get("segment_id") == segment_id
        ]
        assert complete_for_seg, f"Expected segment-complete for segment {segment_id}"

    assert event_names[-1] == "translation-complete"
    assert events[-1][1]["status"] == "completed"

    state = client.get(f"/works/{work.id}/chapters/{chapter.id}/translation")
    assert state.status_code == 200
    payload = state.json()
    assert payload["status"] == "completed"
    assert len(payload["segments"]) == 3
    assert payload["segments"][0]["src"] == "彼は歩く。\n彼女も歩く。"
    assert payload["segments"][0]["tgt"] != ""
    assert payload["segments"][0]["flags"] == []
    assert payload["segments"][1]["src"] == "\n\n"
    assert payload["segments"][1]["tgt"] == ""
    assert payload["segments"][1]["flags"] == ["whitespace"]
    assert payload["segments"][2]["src"] == "場面転換。"
    assert payload["segments"][2]["tgt"] != ""
    assert payload["segments"][2]["flags"] == []


# ---------------------------------------------------------------------------
# Streaming endpoint error boundary tests
# ---------------------------------------------------------------------------


def _make_translated_chapter(db_session: Session, work: Work) -> tuple[Chapter, TranslationSegment]:
    """Create a chapter with one translated segment, returning (chapter, segment)."""
    chapter = Chapter(
        work_id=work.id,
        idx=1,
        sort_key=Decimal(1),
        title="Work #1",
        normalized_text="some text",
        text_hash="some-hash",
    )
    db_session.add(chapter)
    db_session.flush()

    translation = ChapterTranslation(
        chapter_id=chapter.id, status="completed", cache_policy="reuse", params={}
    )
    db_session.add(translation)
    db_session.flush()

    segment = TranslationSegment(
        chapter_translation_id=translation.id,
        start=0,
        end=9,
        order_index=0,
        tgt="translated",
        flags=[],
        src_hash="abc",
    )
    db_session.add(segment)
    db_session.commit()
    db_session.refresh(chapter)
    db_session.refresh(segment)
    return chapter, segment


def test_retranslate_stream_returns_404_for_missing_segment(client, db_session):
    """Invalid segment id must produce HTTP 404 before the SSE stream opens."""
    work = _create_work(db_session, "Retranslate Work")
    chapter, _ = _make_translated_chapter(db_session, work)

    resp = client.get(f"/works/{work.id}/chapters/{chapter.id}/segments/99999/retranslate/stream")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "segment not found"


def test_explain_stream_returns_404_for_missing_segment(client, db_session):
    """Invalid segment id must produce HTTP 404 before the SSE stream opens."""
    work = _create_work(db_session, "Explain Work 404")
    chapter, _ = _make_translated_chapter(db_session, work)

    resp = client.get(f"/works/{work.id}/chapters/{chapter.id}/segments/99999/explain/stream")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "segment not found"


def test_explain_stream_returns_400_for_untranslated_segment(client, db_session):
    """Untranslated segment must produce HTTP 400 before the SSE stream opens."""
    work = _create_work(db_session, "Explain Work 400")
    chapter = Chapter(
        work_id=work.id,
        idx=1,
        sort_key=Decimal(1),
        title="Work #1",
        normalized_text="some text",
        text_hash="untranslated-hash",
    )
    db_session.add(chapter)
    db_session.flush()
    translation = ChapterTranslation(
        chapter_id=chapter.id, status="pending", cache_policy="reuse", params={}
    )
    db_session.add(translation)
    db_session.flush()
    segment = TranslationSegment(
        chapter_translation_id=translation.id,
        start=0,
        end=9,
        order_index=0,
        tgt="",  # not translated
        flags=[],
        src_hash="def",
    )
    db_session.add(segment)
    db_session.commit()
    db_session.refresh(segment)

    resp = client.get(
        f"/works/{work.id}/chapters/{chapter.id}/segments/{segment.id}/explain/stream"
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "segment is not translated"


def test_regenerate_explanation_returns_404_for_missing_segment(client, db_session):
    """Invalid segment id must produce HTTP 404 before the SSE stream opens."""
    work = _create_work(db_session, "Regenerate Work 404")
    chapter, _ = _make_translated_chapter(db_session, work)

    resp = client.post(
        f"/works/{work.id}/chapters/{chapter.id}/segments/99999/regenerate-explanation"
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "segment not found"


def test_regenerate_explanation_returns_400_for_untranslated_segment(client, db_session):
    """Untranslated segment must produce HTTP 400 before the SSE stream opens."""
    work = _create_work(db_session, "Regenerate Work 400")
    chapter, _ = _make_translated_chapter(db_session, work)

    # Reset the segment's tgt to make it untranslated
    segment = db_session.execute(
        select(TranslationSegment).where(
            TranslationSegment.chapter_translation_id
            == db_session.execute(
                select(ChapterTranslation).where(ChapterTranslation.chapter_id == chapter.id)
            )
            .scalar_one()
            .id
        )
    ).scalar_one()
    segment.tgt = ""
    db_session.add(segment)
    db_session.commit()

    resp = client.post(
        f"/works/{work.id}/chapters/{chapter.id}/segments/{segment.id}/regenerate-explanation"
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "segment is not translated"
