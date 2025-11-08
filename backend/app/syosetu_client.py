from __future__ import annotations

import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup


class SyosetuClient:
    base_domain = "https://ncode.syosetu.com"

    async def fetch(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers={"User-Agent": "tonari-prototype/0.1"})
            resp.raise_for_status()
            return resp.text

    def parse_chapter(self, html: str) -> tuple[str, str]:
        soup = BeautifulSoup(html, "lxml")
        # Title can be in h1#novel_subtitle or h1#novel_title depending on page
        title_tag = soup.select_one("#novel_subtitle") or soup.select_one("#novel_title")
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        body = soup.select_one("#novel_honbun")
        if not body:
            # Some pages use #honbun
            body = soup.select_one("#honbun")
        text = "\n".join(p.get_text("\n", strip=False) for p in body.find_all(["p", "div"], recursive=False)) if body else ""
        if not text:
            # Fallback: take all text under #novel_honbun recursively
            body = soup.select_one("#novel_honbun")
            text = body.get_text("\n", strip=False) if body else ""
        return title, normalize_text(text)


def normalize_text(text: str) -> str:
    # Normalize newlines and strip trailing spaces; keep JP punctuation intact
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse more than 2 blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")
