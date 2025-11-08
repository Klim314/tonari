from __future__ import annotations

from typing import List, Dict


def simple_jp_sentence_spans(text: str) -> List[tuple[int, int]]:
    """Naive JP sentence/dialogue splitter returning (start, end) offsets.
    Splits on 。！？ while keeping punctuation with the sentence. Treats quotes as part of the segment.
    """
    if not text:
        return []
    cutset = set("。！？")
    spans: List[tuple[int, int]] = []
    start = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in cutset:
            # include the punctuation
            end = i + 1
            spans.append((start, end))
            # skip following whitespace/newlines
            j = end
            while j < n and text[j] in (" ", "\t", "\n"):
                j += 1
            start = j
            i = j
            continue
        i += 1
    # tail
    if start < n:
        spans.append((start, n))
    # collapse empty spans
    spans = [(s, e) for (s, e) in spans if e > s]
    return spans


def stub_translate(src: str) -> str:
    """Placeholder translation: echoes with a prefix. Replace with LLM call later."""
    return f"[EN draft] {src.strip()}"


def segment_and_translate(text: str) -> List[Dict]:
    """Produce a list of {start,end,tgt,flags} dicts as a stand-in for LLM output."""
    out: List[Dict] = []
    for idx, (start, end) in enumerate(simple_jp_sentence_spans(text)):
        src = text[start:end]
        tgt = stub_translate(src)
        out.append({"start": start, "end": end, "tgt": tgt, "flags": []})
    return out

