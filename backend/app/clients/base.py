from __future__ import annotations

from typing import Mapping, Protocol


class HttpClient(Protocol):
    """Protocol for HTTP clients used by scrapers."""

    def fetch(self, url: str, headers: Mapping[str, str] | None = None) -> str:
        ...
