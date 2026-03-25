from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Chapter, TranslationSegment, Work
from app.syosetu.scraper import SyosetuScraper


def _create_chapter(session: Session, text: str = "彼は歩く。彼女も歩く。") -> Chapter:
    work = Work(title="Test Work", source_meta={"source": "test"})
    session.add(work)
    session.flush()

    chapter = Chapter(
        work_id=work.id,
        idx=1,
        sort_key=Decimal(1),
        title="Chapter 1",
        normalized_text=text,
        text_hash="dummy",
    )
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


def test_create_chapter_translation_flow(client, db_session):
    chapter = _create_chapter(db_session, text="彼は歩く。\n彼女も歩く。\n\n場面転換。")

    resp = client.post("/chapter-translations/", json={"chapter_id": chapter.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["chapter_id"] == chapter.id
    assert data["status"] == "completed"

    ct_id = data["id"]
    resp = client.get(f"/chapter-translations/{ct_id}/segments")
    assert resp.status_code == 200
    segments = resp.json()
    assert len(segments) == 3
    assert segments[0]["src"] == "彼は歩く。\n彼女も歩く。"
    assert segments[0]["tgt"] != ""
    assert segments[0]["flags"] == []
    assert segments[1]["src"] == "\n\n"
    assert segments[1]["tgt"] == ""
    assert segments[1]["flags"] == ["whitespace"]
    assert segments[2]["src"] == "場面転換。"
    assert segments[2]["tgt"] != ""
    assert segments[2]["flags"] == []

    db_session.expire_all()
    rows = (
        db_session.execute(
            select(TranslationSegment).where(TranslationSegment.chapter_translation_id == ct_id)
        )
        .scalars()
        .all()
    )
    assert len(rows) == 3
    assert rows[0].order_index == 0


def test_create_chapter_translation_missing_chapter(client):
    resp = client.post("/chapter-translations/", json={"chapter_id": 999})
    assert resp.status_code == 404


def test_ingest_syosetu_creates_chapter(monkeypatch, client):
    captured: dict[str, str] = {}

    def fake_scrape(self, url: str) -> tuple[str, str]:
        captured["url"] = url
        return "Fake Title", "一文です。二文です。"

    monkeypatch.setattr(SyosetuScraper, "scrape_chapter", fake_scrape)

    resp = client.post("/ingest/syosetu", json={"novel_id": "n1234ab", "chapter": 2})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["title"] == "Fake Title"
    assert payload["idx"] == 1
    assert captured["url"] == "https://ncode.syosetu.com/n1234ab/2/"

    with SessionLocal() as verify_session:
        chapters = verify_session.execute(select(Chapter)).scalars().all()
        assert len(chapters) == 1
        assert chapters[0].normalized_text.startswith("一文です")
