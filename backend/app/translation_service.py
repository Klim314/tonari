from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. Suspendisse "
    "lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed, dolor."
)


@dataclass(slots=True)
class SegmentSlice:
    start: int
    end: int
    text: str
    requires_translation: bool


def newline_segment_slices(text: str) -> List[SegmentSlice]:
    """Split text into newline-delimited segments, collapsing consecutive blank lines."""
    if not text:
        return []

    segments: List[SegmentSlice] = []
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
            if cursor > anchor:
                append_segment(anchor, cursor, True)
            newline_start = cursor
            while cursor < n and text[cursor] == "\n":
                cursor += 1
            append_segment(newline_start, cursor, False)
            anchor = cursor
            continue
        cursor += 1

    if anchor < n:
        append_segment(anchor, n, True)

    return segments


def build_lorem_text(min_chars: int) -> str:
    if min_chars <= 0:
        return ""
    repeats = (min_chars // len(LOREM)) + 1
    text = (LOREM + " ") * repeats
    return text[:min_chars].strip()


def stub_translate(src: str) -> str:
    """Placeholder translation that emits lorem ipsum proportionate to src length."""
    return build_lorem_text(max(len(src.strip()), 16))


async def stream_lorem_translation(src: str, *, chunk_size: int = 24) -> AsyncGenerator[str, None]:
    lorem = stub_translate(src)
    for idx in range(0, len(lorem), chunk_size):
        await asyncio.sleep(0.05)
        yield lorem[idx : idx + chunk_size]


def segment_and_translate(text: str) -> List[Dict]:
    """Produce a list of {start,end,tgt,flags} dicts as a stand-in for LLM output."""
    out: List[Dict] = []
    for segment in newline_segment_slices(text):
        flags: List[str] = []
        if not segment.requires_translation:
            flags.append("whitespace")
            tgt = ""
        else:
            src = segment.text
            tgt = stub_translate(src)
        out.append({"start": segment.start, "end": segment.end, "tgt": tgt, "flags": flags})
    return out

