from __future__ import annotations

from typing import Protocol

from .types import SourceDescriptor, WorkMetadata


class WorkScraper(Protocol):
    source: str
    hostnames: set[str]

    def matches(self, url: str) -> bool:
        ...

    def parse_descriptor(self, url: str) -> SourceDescriptor:
        ...

    def fetch_work_metadata(self, descriptor: SourceDescriptor) -> WorkMetadata:
        ...
