from __future__ import annotations

import re
from bs4 import BeautifulSoup


_TITLE_SELECTORS = ["#novel_subtitle", "#novel_title", "h1.p-novel__title"]
_BODY_SELECTORS = ["#novel_honbun", "#honbun", "div.p-novel__body"]


def parse_chapter(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup)
    body_text = _extract_body(soup)
    return title, normalize_text(body_text)


def _extract_title(soup: BeautifulSoup) -> str:
    for selector in _TITLE_SELECTORS:
        tag = soup.select_one(selector)
        if tag:
            return tag.get_text(strip=True)
    return "Untitled"


def _extract_body(soup: BeautifulSoup) -> str:
    for selector in _BODY_SELECTORS:
        node = soup.select_one(selector)
        if not node:
            continue
        if selector == "div.p-novel__body":
            text = _extract_modern_body(node)
        else:
            text = "\n".join(
                child.get_text("\n", strip=False)
                for child in node.find_all(["p", "div"], recursive=False)
            )
        text = text or node.get_text("\n", strip=False)
        if text.strip():
            return text
    fallback = soup.select_one("#novel_honbun") or soup.select_one("#honbun")
    if fallback:
        return fallback.get_text("\n", strip=False)
    return ""


def _extract_modern_body(body):
    blocks = body.select(".js-novel-text")
    if not blocks:
        return body.get_text("\n", strip=False)
    lines = []
    for block in blocks:
        block_text = block.get_text("\n", strip=False)
        lines.append(block_text)
    return "\n".join(lines)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")
