from __future__ import annotations


def sanitize_pagination(limit: int, offset: int, max_limit: int = 100) -> tuple[int, int]:
    """Clamp pagination inputs to sane defaults."""
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return limit, offset
