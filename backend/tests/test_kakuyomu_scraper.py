from decimal import Decimal
from pathlib import Path

import pytest

from app.kakuyomu.scraper import KakuyomuScraper
from app.scrapers.exceptions import ScraperError
from services.scrape_manager import _source_chapter_id_from_url

FIXTURES = Path(__file__).parent / "fixtures" / "kakuyomu"
WORK_ID = "16818622172873736209"
FIRST_EPISODE_ID = "16818622172873813123"
WORK_URL = f"https://kakuyomu.jp/works/{WORK_ID}"
EPISODE_URL = f"https://kakuyomu.jp/works/{WORK_ID}/episodes/{FIRST_EPISODE_ID}"


class FixtureHttpClient:
    """HttpClient that serves saved fixtures instead of hitting the network."""

    def __init__(self) -> None:
        self.work_html = (FIXTURES / "work.html").read_text(encoding="utf-8")
        self.episode_html = (FIXTURES / "episode.html").read_text(encoding="utf-8")
        self.requested: list[str] = []

    def fetch(self, url: str, headers=None) -> str:
        self.requested.append(url)
        if "/episodes/" in url:
            return self.episode_html
        return self.work_html


@pytest.fixture
def scraper() -> KakuyomuScraper:
    return KakuyomuScraper(http_client=FixtureHttpClient())


def test_matches():
    scraper = KakuyomuScraper(http_client=FixtureHttpClient())
    assert scraper.matches("https://kakuyomu.jp/works/123")
    assert not scraper.matches("https://ncode.syosetu.com/n4811fg/")


def test_parse_descriptor_work_url(scraper):
    descriptor = scraper.parse_descriptor(WORK_URL)
    assert descriptor.source == "kakuyomu"
    assert descriptor.source_id == WORK_ID
    assert descriptor.url == WORK_URL


def test_parse_descriptor_episode_url_normalizes_to_work(scraper):
    descriptor = scraper.parse_descriptor(EPISODE_URL)
    assert descriptor.source_id == WORK_ID
    assert descriptor.url == WORK_URL


def test_parse_descriptor_rejects_bad_url(scraper):
    with pytest.raises(ScraperError):
        scraper.parse_descriptor("https://kakuyomu.jp/")


def test_fetch_work_metadata_populates_and_caches(scraper):
    descriptor = scraper.parse_descriptor(WORK_URL)
    metadata = scraper.fetch_work_metadata(descriptor)

    assert metadata.source == "kakuyomu"
    assert metadata.source_id == WORK_ID
    assert "魔物" in metadata.title
    assert metadata.author == "Mikura"
    assert metadata.homepage_url == WORK_URL
    assert metadata.extra["chapter_count"] == 108
    assert metadata.extra["episode_ids"][0] == FIRST_EPISODE_ID
    # TOC is now cached, so build_chapter_url should not need another fetch.
    assert scraper._toc_cache[WORK_ID][0] == FIRST_EPISODE_ID


def test_build_chapter_url_first_and_last(scraper):
    url = scraper.build_chapter_url(WORK_ID, Decimal(1))
    assert url == EPISODE_URL
    last = scraper.build_chapter_url(WORK_ID, Decimal(108))
    assert last.startswith(f"https://kakuyomu.jp/works/{WORK_ID}/episodes/")


def test_build_chapter_url_lazily_fetches_toc():
    client = FixtureHttpClient()
    scraper = KakuyomuScraper(http_client=client)
    # No prior fetch_work_metadata call; build_chapter_url must fetch the work page.
    url = scraper.build_chapter_url(WORK_ID, Decimal(1))
    assert url == EPISODE_URL
    assert any("/episodes/" not in r for r in client.requested)  # fetched the TOC page


def test_build_chapter_url_out_of_range(scraper):
    with pytest.raises(ScraperError):
        scraper.build_chapter_url(WORK_ID, Decimal(999))


def test_build_chapter_url_refreshes_stale_toc():
    """A short cached TOC is refreshed before raising out-of-range (running works)."""
    client = FixtureHttpClient()
    scraper = KakuyomuScraper(http_client=client)
    # Simulate a stale cache that predates newly published episodes.
    scraper._toc_cache[WORK_ID] = ["stale-only-episode"]
    url = scraper.build_chapter_url(WORK_ID, Decimal(50))
    assert "/episodes/" in url
    # The cache was refreshed from the (108-episode) work page.
    assert len(scraper._toc_cache[WORK_ID]) == 108
    assert any("/episodes/" not in r for r in client.requested)


def test_build_chapter_url_rejects_fractional(scraper):
    with pytest.raises(ScraperError):
        scraper.build_chapter_url(WORK_ID, Decimal("1.5"))


def test_scrape_chapter(scraper):
    title, text = scraper.scrape_chapter(EPISODE_URL)
    assert title == "第1話"
    assert text


def test_source_chapter_id_extraction():
    assert _source_chapter_id_from_url(EPISODE_URL) == FIRST_EPISODE_ID
    # Syosetu-style trailing-slash chapter number.
    assert _source_chapter_id_from_url("https://ncode.syosetu.com/n4811fg/3/") == "3"
    # Query strings and fragments don't leak into the id.
    assert _source_chapter_id_from_url(f"{EPISODE_URL}?utm=x#top") == FIRST_EPISODE_ID
