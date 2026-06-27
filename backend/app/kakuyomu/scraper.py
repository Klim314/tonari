from __future__ import annotations

from decimal import Decimal
from urllib.parse import urlparse

from app.clients import HttpClient, RequestsClient
from app.scrapers import scraper_registry
from app.scrapers.exceptions import ScraperError
from app.scrapers.types import SourceDescriptor, WorkMetadata

from . import parser as kakuyomu_parser

_HOSTNAME = "kakuyomu.jp"


class KakuyomuScraper:
    """Fetches and parses Kakuyomu data using a pluggable HTTP client.

    Kakuyomu episodes are addressed by opaque ids rather than sequential numbers, so
    the ordered episode-id list is read from the work page's embedded data and cached
    per work id. ``build_chapter_url`` then maps a 1-based positional chapter number
    to the corresponding episode id.
    """

    source = "kakuyomu"
    hostnames = {_HOSTNAME}

    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or RequestsClient()
        # work_id -> ordered list of episode ids
        self._toc_cache: dict[str, list[str]] = {}

    def matches(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return netloc == _HOSTNAME or netloc.endswith(f".{_HOSTNAME}")

    def parse_descriptor(self, url: str) -> SourceDescriptor:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        # Expected: ["works", "<work_id>", ("episodes", "<episode_id>")?]
        if len(parts) < 2 or parts[0] != "works":
            raise ScraperError("Unable to determine Kakuyomu work id from URL")
        work_id = parts[1]
        return SourceDescriptor(
            source=self.source,
            source_id=work_id,
            url=self._build_work_url(work_id),
        )

    def fetch_work_metadata(self, descriptor: SourceDescriptor) -> WorkMetadata:
        html = self.http_client.fetch(descriptor.url)
        data = kakuyomu_parser.parse_work_page(html, descriptor.source_id)
        episode_ids = [episode_id for episode_id, _ in data.episodes]
        self._toc_cache[descriptor.source_id] = episode_ids
        extra = {
            "raw_url": descriptor.url,
            "source": self.source,
            "source_id": descriptor.source_id,
            "chapter_count": len(episode_ids),
            "episode_ids": episode_ids,
            "genre": data.genre,
            "serial_status": data.serial_status,
            "total_character_count": data.total_character_count,
        }
        return WorkMetadata(
            source=self.source,
            source_id=descriptor.source_id,
            title=data.title,
            author=data.author,
            description=data.description,
            homepage_url=descriptor.url,
            thumbnail_url=data.thumbnail_url,
            extra=extra,
        )

    def scrape_chapter(self, url: str) -> tuple[str, str]:
        html = self.http_client.fetch(url)
        return kakuyomu_parser.parse_chapter(html)

    def build_chapter_url(self, source_id: str, chapter_number: Decimal) -> str:
        integer_value = chapter_number.to_integral_value()
        if chapter_number != integer_value:
            raise ScraperError("Kakuyomu chapters are indexed by whole numbers")
        index = int(integer_value)
        if index < 1:
            raise ScraperError("Chapter numbers must be >= 1")

        episode_ids = self._episode_ids(source_id)
        if index > len(episode_ids):
            # The cached TOC may be stale for a still-serializing work; refresh once
            # before giving up so re-scrapes pick up newly published episodes without
            # a process restart.
            episode_ids = self._episode_ids(source_id, refresh=True)
        if index > len(episode_ids):
            raise ScraperError(
                f"Chapter {index} is out of range (work has {len(episode_ids)} episodes)"
            )
        episode_id = episode_ids[index - 1]
        return f"https://{_HOSTNAME}/works/{source_id}/episodes/{episode_id}"

    def _episode_ids(self, source_id: str, *, refresh: bool = False) -> list[str]:
        """Return cached episode ids for the work, fetching the TOC if needed.

        Pass ``refresh=True`` to bypass the cache and re-fetch (e.g. when a requested
        index exceeds the cached length on a work that is still being serialized).
        """
        cached = self._toc_cache.get(source_id)
        if cached is None or refresh:
            html = self.http_client.fetch(self._build_work_url(source_id))
            data = kakuyomu_parser.parse_work_page(html, source_id)
            cached = [episode_id for episode_id, _ in data.episodes]
            self._toc_cache[source_id] = cached
        return cached

    @staticmethod
    def _build_work_url(work_id: str) -> str:
        return f"https://{_HOSTNAME}/works/{work_id}"


scraper_registry.register(KakuyomuScraper())
