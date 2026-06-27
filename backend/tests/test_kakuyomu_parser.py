from pathlib import Path

import pytest

from app.kakuyomu.parser import parse_chapter, parse_work_page

FIXTURES = Path(__file__).parent / "fixtures" / "kakuyomu"
WORK_ID = "16818622172873736209"
FIRST_EPISODE_ID = "16818622172873813123"


@pytest.fixture(scope="module")
def work_html() -> str:
    return (FIXTURES / "work.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def episode_html() -> str:
    return (FIXTURES / "episode.html").read_text(encoding="utf-8")


def test_parse_work_page_returns_full_ordered_toc(work_html):
    data = parse_work_page(work_html, WORK_ID)

    # The rendered DOM only exposes ~7 links; the full TOC comes from the embedded JSON.
    assert len(data.episodes) == 108
    episode_ids = [episode_id for episode_id, _ in data.episodes]
    assert len(set(episode_ids)) == 108  # unique
    assert episode_ids[0] == FIRST_EPISODE_ID  # ordered, first episode first


def test_parse_work_page_extracts_metadata(work_html):
    data = parse_work_page(work_html, WORK_ID)

    assert data.work_id == WORK_ID
    assert "魔物" in data.title
    assert data.author == "Mikura"
    assert data.genre == "FANTASY"
    assert data.serial_status == "RUNNING"
    assert data.description


def test_parse_work_page_rejects_unknown_work(work_html):
    from app.scrapers.exceptions import ScraperError

    with pytest.raises(ScraperError):
        parse_work_page(work_html, "0000000000000000000")


def test_parse_chapter_title_and_body(episode_html):
    title, text = parse_chapter(episode_html)

    assert title == "第1話"
    assert text
    # Leading full-width indent is preserved.
    assert "　" in text


def test_parse_chapter_strips_furigana_readings(episode_html):
    # The first episode uses sesame-dot emphasis ruby (<rt>・</rt>); the reading
    # markers must not leak into the extracted prose. (Full-width parens that appear
    # in the prose itself are dialogue, not ruby fallback parens, so they remain.)
    _, text = parse_chapter(episode_html)
    assert "・" not in text
