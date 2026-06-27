from __future__ import annotations

import re


def remove_ruby_annotations(element) -> None:
    """Strip furigana annotation tags (rt, rp) from a BeautifulSoup element tree.

    Leaves the base reading (the ``<rb>`` / bare text inside ``<ruby>``) intact so
    the resulting text contains the kanji rather than the kana gloss.
    """
    for tag in element.find_all(["rt", "rp"]):
        tag.decompose()


def normalize_text(text: str) -> str:
    """Normalize scraped chapter text: unify newlines and collapse blank runs."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")
