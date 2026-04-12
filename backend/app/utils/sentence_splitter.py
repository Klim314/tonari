from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class SentenceSpan:
    span_start: int
    span_end: int
    text: str


class SentenceSplitter(Protocol):
    def split(self, text: str) -> list[SentenceSpan]: ...


class GreedySentenceSplitter:
    """Rule-based Japanese sentence splitter.

    Splits on terminal punctuation greedily: runs of 。 ？ ！ … ? ! are
    treated as a single sentence terminator. Trailing whitespace after a
    terminator is consumed into the preceding sentence rather than starting a
    new one. Empty spans are silently dropped.
    """

    _TERMINATOR_RE = re.compile(r"[。？！…?!]+[ \u3000\t]*")

    def split(self, text: str) -> list[SentenceSpan]:
        if not text:
            return []

        spans: list[SentenceSpan] = []
        n = len(text)
        start = 0

        for match in self._TERMINATOR_RE.finditer(text):
            end = match.end()
            span_text = text[start:end]
            if span_text.strip():
                spans.append(SentenceSpan(span_start=start, span_end=end, text=span_text))
            start = end

        # Remainder after the last terminator (or the whole string if no
        # terminator was found).
        if start < n:
            remainder = text[start:]
            if remainder.strip():
                spans.append(SentenceSpan(span_start=start, span_end=n, text=remainder))

        return spans


_default_splitter = GreedySentenceSplitter()


def get_sentence_splitter() -> SentenceSplitter:
    return _default_splitter


__all__ = [
    "SentenceSpan",
    "SentenceSplitter",
    "GreedySentenceSplitter",
    "get_sentence_splitter",
]
