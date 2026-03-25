from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class HttpClient(Protocol):
    """Protocol for HTTP clients used by scrapers."""

    def fetch(self, url: str, headers: Mapping[str, str] | None = None) -> str: ...
