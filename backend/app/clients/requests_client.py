from __future__ import annotations

from typing import Mapping

import requests

from .base import HttpClient


class RequestsClient(HttpClient):
    """Minimal requests-based HTTP client used by scrapers."""

    def __init__(self, *, timeout: float = 20.0, user_agent: str | None = None) -> None:
        self.timeout = timeout
        self.default_headers = {"User-Agent": user_agent or "tonari-prototype/0.1"}

    def fetch(self, url: str, headers: Mapping[str, str] | None = None) -> str:
        final_headers = dict(self.default_headers)
        if headers:
            final_headers.update(headers)
        resp = requests.get(url, headers=final_headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text
