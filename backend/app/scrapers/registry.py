from __future__ import annotations

from collections.abc import Iterable
from typing import List
from urllib.parse import urlparse

from .base import WorkScraper
from .exceptions import ScraperNotFoundError


class ScraperRegistry:
    def __init__(self) -> None:
        self._scrapers: List[WorkScraper] = []

    def register(self, scraper: WorkScraper) -> None:
        self._scrapers.append(scraper)

    def bulk_register(self, scrapers: Iterable[WorkScraper]) -> None:
        for scraper in scrapers:
            self.register(scraper)

    def resolve(self, url: str) -> WorkScraper:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        for scraper in self._scrapers:
            if hostname in scraper.hostnames or scraper.matches(url):
                return scraper
        raise ScraperNotFoundError(f"No scraper available for URL: {url}")


scraper_registry = ScraperRegistry()
