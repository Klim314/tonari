from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(slots=True)
class SegmentSlice:
    start: int
    end: int
    text: str
    requires_translation: bool


def newline_segment_slices(text: str) -> list[SegmentSlice]:
    """Split text into segments separated by at least two consecutive newlines.

    This keeps related content (like bullet points) together in the same segment.
    Content separated by blank lines (2+ newlines) is treated as separate segments.
    """
    if not text:
        return []

    segments: list[SegmentSlice] = []
    cursor = 0
    anchor = 0
    n = len(text)

    def append_segment(seg_start: int, seg_end: int, require_translation: bool) -> None:
        if seg_start >= seg_end:
            return
        segments.append(
            SegmentSlice(
                start=seg_start,
                end=seg_end,
                text=text[seg_start:seg_end],
                requires_translation=require_translation,
            )
        )

    while cursor < n:
        char = text[cursor]
        if char == "\n":
            newline_start = cursor
            # Count consecutive newlines
            newline_count = 0
            while cursor < n and text[cursor] == "\n":
                newline_count += 1
                cursor += 1

            # Only create a segment boundary if we have 2+ newlines (i.e., a blank line)
            if newline_count >= 2:
                # Append the content before the newlines
                if newline_start > anchor:
                    append_segment(anchor, newline_start, True)
                # Append the whitespace segment
                append_segment(newline_start, cursor, False)
                anchor = cursor
            # Otherwise, just skip the newline and keep going (merge with next line)
            continue
        cursor += 1

    if anchor < n:
        append_segment(anchor, n, True)

    return segments


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
