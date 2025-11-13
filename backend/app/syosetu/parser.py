from __future__ import annotations

import re

from bs4 import BeautifulSoup

_TITLE_SELECTORS = ["#novel_subtitle", "#novel_title", "h1.p-novel__title"]
_BODY_SELECTORS = ["#novel_honbun", "#honbun", "div.p-novel__body"]


def _remove_ruby_annotations(element) -> None:
    """Remove ruby annotation tags (rt, rp) from the element tree."""
    for tag in element.find_all(["rt", "rp"]):
        tag.decompose()


def _get_paragraph_text(element) -> str:
    """Extract text from element, preserving paragraph structure but not ruby spacing."""
    # For paragraphs/divs, get each child's text separately and join with newlines
    children = element.find_all(["p", "div"], recursive=False)
    if children:
        return "\n".join(child.get_text(separator="", strip=False) for child in children)
    # For inline content or single paragraphs, use empty separator to avoid ruby spacing issues
    return element.get_text(separator="", strip=False)


def parse_chapter(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup)
    body_text = _extract_body(soup)
    return title, normalize_text(body_text)


def _extract_title(soup: BeautifulSoup) -> str:
    for selector in _TITLE_SELECTORS:
        tag = soup.select_one(selector)
        if tag:
            _remove_ruby_annotations(tag)
            return tag.get_text(strip=True)
    return "Untitled"


def _extract_body(soup: BeautifulSoup) -> str:
    for selector in _BODY_SELECTORS:
        node = soup.select_one(selector)
        if not node:
            continue
        _remove_ruby_annotations(node)
        if selector == "div.p-novel__body":
            text = _extract_modern_body(node)
        else:
            text = "\n".join(
                _get_paragraph_text(child)
                for child in node.find_all(["p", "div"], recursive=False)
            )
        text = text or _get_paragraph_text(node)
        if text.strip():
            return text
    fallback = soup.select_one("#novel_honbun") or soup.select_one("#honbun")
    if fallback:
        _remove_ruby_annotations(fallback)
        return _get_paragraph_text(fallback)
    return ""


def _extract_modern_body(body):
    blocks = body.select(".js-novel-text")
    if not blocks:
        return _get_paragraph_text(body)
    lines = []
    for block in blocks:
        block_text = _get_paragraph_text(block)
        lines.append(block_text)
    return "\n".join(lines)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")
