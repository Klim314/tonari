from __future__ import annotations

from decimal import Decimal
from typing import Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.clients import HttpClient, RequestsClient
from app.scrapers import scraper_registry
from app.scrapers.exceptions import ScraperError
from app.scrapers.types import SourceDescriptor, WorkMetadata
from . import parser as syosetu_parser

_WORK_TITLE_SELECTORS = ["#novel_title", "h1.p-novel__title"]
_WORK_AUTHOR_SELECTORS = ["#novel_writername", ".p-novel__author"]
_WORK_DESC_SELECTORS = ["#novel_ex", ".p-novel__introduction"]


class SyosetuScraper:
    """Fetches and parses Syosetu data using a pluggable HTTP client."""

    source = "syosetu"
    hostnames = {"ncode.syosetu.com"}

    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or RequestsClient()

    def matches(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc.lower().endswith("ncode.syosetu.com")

    def parse_descriptor(self, url: str) -> SourceDescriptor:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            raise ScraperError("Unable to determine Syosetu novel id from URL")
        novel_id = parts[0].lower()
        chapter_id = None
        if len(parts) > 1 and parts[1].isdigit():
            chapter_id = int(parts[1])
        normalized_url = self._build_work_url(novel_id)
        return SourceDescriptor(
            source=self.source,
            source_id=novel_id,
            url=normalized_url,
            chapter_id=chapter_id,
        )

    def fetch_work_metadata(self, descriptor: SourceDescriptor) -> WorkMetadata:
        html = self.http_client.fetch(descriptor.url)
        soup = BeautifulSoup(html, "lxml")
        title = _extract_text(soup, _WORK_TITLE_SELECTORS) or descriptor.source_id
        author = _extract_text(soup, _WORK_AUTHOR_SELECTORS)
        description = _extract_text(soup, _WORK_DESC_SELECTORS)
        thumbnail_url = _extract_thumbnail_url(soup)
        extra = {
            "raw_url": descriptor.url,
            "source": self.source,
            "source_id": descriptor.source_id,
        }
        return WorkMetadata(
            source=self.source,
            source_id=descriptor.source_id,
            title=title,
            author=author,
            description=description,
            homepage_url=descriptor.url,
            thumbnail_url=thumbnail_url,
            extra=extra,
        )

    def scrape_chapter(self, url: str) -> Tuple[str, str]:
        html = self.http_client.fetch(url)
        return syosetu_parser.parse_chapter(html)

    def build_chapter_url(self, source_id: str, chapter_number: Decimal) -> str:
        integer_value = chapter_number.to_integral_value()
        if chapter_number != integer_value:
            raise ScraperError("Syosetu chapters only support whole numbers")
        chapter_index = int(integer_value)
        if chapter_index < 1:
            raise ScraperError("Chapter numbers must be >= 1")
        novel_id = source_id.strip().lower()
        return f"https://ncode.syosetu.com/{novel_id}/{chapter_index}/"

    @staticmethod
    def _build_work_url(novel_id: str) -> str:
        return f"https://ncode.syosetu.com/{novel_id}/"


def _extract_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return node.get_text(strip=True)
    return None


def _extract_thumbnail_url(soup: BeautifulSoup) -> str | None:
    meta = soup.select_one('meta[property="og:image"]') or soup.select_one(
        'meta[name="twitter:image"]'
    )
    if meta and meta.has_attr("content"):
        return meta["content"].strip() or None
    img = soup.select_one(".p-novel__thumbnail img")
    if img and img.has_attr("src"):
        return img["src"].strip() or None
    return None


scraper_registry.register(SyosetuScraper())
