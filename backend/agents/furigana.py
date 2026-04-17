"""Reliable furigana/reading generation using MeCab (via fugashi).

Instead of asking the LLM to produce readings (which hallucinates),
we run the surface form through MeCab after the fact.
"""

from __future__ import annotations

import logging
import re

import fugashi

logger = logging.getLogger(__name__)

_tagger: fugashi.Tagger | None = None

# Surface forms that are entirely kana (hiragana/katakana) don't need a reading.
_KANA_ONLY = re.compile(r"^[\u3040-\u309F\u30A0-\u30FF\u30FC\u3000-\u303Fー]+$")


def _get_tagger() -> fugashi.Tagger:
    global _tagger
    if _tagger is None:
        _tagger = fugashi.Tagger()
    return _tagger


def _kata_to_hira(text: str) -> str:
    """Convert katakana characters to hiragana."""
    return "".join(
        chr(ord(ch) - 0x60) if "\u30A1" <= ch <= "\u30F6" else ch for ch in text
    )


def get_reading(surface: str) -> str | None:
    """Return the hiragana reading for a Japanese surface form.

    Returns ``None`` when the surface is already all-kana (reading would be
    redundant) or when MeCab cannot determine a reading.
    """
    if not surface or _KANA_ONLY.match(surface):
        return None

    try:
        tagger = _get_tagger()
        words = tagger(surface)
    except Exception:
        logger.warning("furigana: MeCab failed for %r", surface, exc_info=True)
        return None

    parts: list[str] = []
    for word in words:
        kana = getattr(word.feature, "kana", None)
        if kana:
            parts.append(_kata_to_hira(kana))
        else:
            # Fallback: use the surface itself (e.g. for symbols, punctuation)
            parts.append(word.surface)

    reading = "".join(parts)

    # If the reading is identical to the surface, it's redundant
    if reading == surface:
        return None

    return reading
