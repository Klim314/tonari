from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Dict, List

from agents.translation_agent import get_translation_agent

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


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def async_segment_and_translate(text: str) -> List[Dict]:
    agent = get_translation_agent()
    out: List[Dict] = []
    context_limit = max(0, getattr(agent, "context_window", 0))
    context_buffer: List[Dict[str, str]] = []
    for segment in newline_segment_slices(text):
        flags: List[str] = []
        tgt = ""
        if not segment.requires_translation:
            flags.append("whitespace")
        else:
            preceding = list(context_buffer) if context_limit > 0 and context_buffer else None
            tgt = await agent.translate_segment(
                segment.text, preceding_segments=preceding
            )
            if context_limit > 0:
                src_for_context = segment.text.strip()
                tgt_for_context = tgt.strip()
                if src_for_context and tgt_for_context:
                    context_buffer.append({"src": src_for_context, "tgt": tgt_for_context})
                    if len(context_buffer) > context_limit:
                        context_buffer.pop(0)
        out.append({"start": segment.start, "end": segment.end, "tgt": tgt, "flags": flags})
    return out


def segment_and_translate(text: str) -> List[Dict]:
    return asyncio.run(async_segment_and_translate(text))
