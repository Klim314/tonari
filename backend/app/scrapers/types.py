from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SourceDescriptor:
    source: str
    source_id: str
    url: str
    chapter_id: int | None = None


@dataclass(slots=True)
class WorkMetadata:
    source: str
    source_id: str
    title: str
    homepage_url: str
    author: str | None = None
    description: str | None = None
    extra: dict[str, Any] | None = None
