from __future__ import annotations

from typing import Tuple

from app.clients import HttpClient, RequestsClient
from . import parser as syosetu_parser


class SyosetuScraper:
    """Fetches and parses Syosetu chapters using a pluggable HTTP client."""

    def __init__(self, http_client: HttpClient | None = None) -> None:
        self.http_client = http_client or RequestsClient()

    def scrape_chapter(self, url: str) -> Tuple[str, str]:
        html = self.http_client.fetch(url)
        return syosetu_parser.parse_chapter(html)
