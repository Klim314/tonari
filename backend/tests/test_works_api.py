from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chapter, Work
from app.syosetu.scraper import SyosetuScraper


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
    assert payload["total"] == 3
    assert payload["items"][0]["title"] == "Chronicles #1"
    assert payload["items"][1]["idx"] == 2

    resp2 = client.get(f"/works/{work.id}/chapters?offset=2")
    assert resp2.status_code == 200
    payload2 = resp2.json()
    assert len(payload2["items"]) == 1
    assert payload2["items"][0]["idx"] == 3


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
        json={"start": 1, "end": 3.5, "force": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "partial"
    assert data["work_id"] == work.id
    assert data["force"] is True
    assert data["start"] == 1.0
    assert data["end"] == 3.5
    assert data["requested"] == 4
    assert data["created"] == 3
    assert data["updated"] == 0
    assert data["skipped"] == 0
    assert len(data["errors"]) == 1
    assert data["errors"][0]["chapter"] == 3.5
    assert "whole numbers" in data["errors"][0]["reason"]

    rows = db_session.execute(select(Chapter).where(Chapter.work_id == work.id)).scalars().all()
    assert len(rows) == 3


def test_scrape_chapters_missing_work(client):
    resp = client.post("/works/999/scrape-chapters", json={"start": 1, "end": 2})
    assert resp.status_code == 404


def test_scrape_chapters_without_source(client, db_session):
    work = Work(title="Loose Work")
    db_session.add(work)
    db_session.commit()

    resp = client.post(f"/works/{work.id}/scrape-chapters", json={"start": 1, "end": 2})
    assert resp.status_code == 400


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
