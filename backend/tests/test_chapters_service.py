from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.models import Chapter, Work
from app.scrapers import scraper_registry
from services.chapters import ChaptersService


class FakeScraper:
    source = "fake"
    hostnames: set[str] = set()

    def matches(self, url: str) -> bool:  # pragma: no cover - unused in tests
        return False

    def parse_descriptor(self, url: str):  # pragma: no cover - unused in tests
        raise NotImplementedError

    def fetch_work_metadata(self, descriptor):  # pragma: no cover - unused
        raise NotImplementedError

    def build_chapter_url(self, source_id: str, chapter_number: Decimal) -> str:
        return f"https://fake/{source_id}/{str(chapter_number)}"

    def scrape_chapter(self, url: str) -> tuple[str, str]:
        chapter_id = url.split("/")[-1]
        chapter_value = Decimal(chapter_id)
        normalized = chapter_value.normalize()
        label = str(normalized)
        return f"Chapter {label}", f"Body {label}"


def _attach_fake_scraper(monkeypatch) -> None:
    fake = FakeScraper()
    monkeypatch.setattr(scraper_registry, "_scrapers", [fake])


def test_scrape_creates_new_chapters(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Fake Work", source="fake", source_id="novel-1")
    db_session.add(work)
    db_session.commit()

    service = ChaptersService(db_session)
    summary = service.scrape_work_for_chapters(work, start=1, end=2, force=False)

    assert summary.requested == 2
    assert summary.created == 2
    rows = db_session.execute(select(Chapter).where(Chapter.work_id == work.id)).scalars().all()
    assert len(rows) == 2
    sort_keys = [row.sort_key for row in rows]
    assert Decimal("1.0000") in sort_keys
    assert Decimal("2.0000") in sort_keys


def test_scrape_skips_when_hash_matches(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Fake Work", source="fake", source_id="novel-2")
    db_session.add(work)
    db_session.flush()

    existing = Chapter(
        work_id=work.id,
        idx=1,
        sort_key=Decimal("1.0000"),
        title="Old",
        normalized_text="Body 1",
        text_hash=ChaptersService._hash_text("Body 1"),
    )
    db_session.add(existing)
    db_session.commit()

    service = ChaptersService(db_session)
    summary = service.scrape_work_for_chapters(work, start=1, end=1, force=False)

    assert summary.skipped == 1
    assert summary.updated == 0
    assert summary.created == 0


def test_scrape_updates_with_force_and_decimal_range(db_session, monkeypatch):
    _attach_fake_scraper(monkeypatch)
    work = Work(title="Fake Work", source="fake", source_id="novel-3")
    db_session.add(work)
    db_session.flush()

    existing = Chapter(
        work_id=work.id,
        idx=2,
        sort_key=Decimal("2.0000"),
        title="Old 2",
        normalized_text="Stale",
        text_hash=ChaptersService._hash_text("Stale"),
    )
    db_session.add(existing)
    db_session.commit()

    service = ChaptersService(db_session)
    summary = service.scrape_work_for_chapters(
        work,
        start=Decimal("1.5"),
        end=Decimal("2.5"),
        force=True,
    )

    assert summary.requested == 3
    assert summary.created == 2  # 1.5 and 2.5
    assert summary.updated == 1  # existing 2.0 forced update
    rows = (
        db_session.execute(
            select(Chapter).where(Chapter.work_id == work.id).order_by(Chapter.sort_key.asc())
        )
        .scalars()
        .all()
    )
    assert [row.sort_key for row in rows] == [
        Decimal("1.5000"),
        Decimal("2.0000"),
        Decimal("2.5000"),
    ]
