from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from app.scrapers.exceptions import ScraperError
from app.scrapers.text import normalize_text, remove_ruby_annotations

# Episode (chapter) page selectors.
_EPISODE_TITLE_SELECTOR = "p.widget-episodeTitle"
_EPISODE_BODY_SELECTOR = "div.js-episode-body"

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.S,
)


@dataclass(slots=True)
class WorkPageData:
    """Parsed contents of a Kakuyomu work (table-of-contents) page."""

    work_id: str
    title: str
    # Ordered list of (episode_id, episode_title) for every episode in the work.
    episodes: list[tuple[str, str]] = field(default_factory=list)
    author: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    genre: str | None = None
    serial_status: str | None = None
    total_character_count: int | None = None


def _load_apollo_state(html: str) -> dict[str, Any]:
    """Extract the Apollo normalized cache embedded in the page's __NEXT_DATA__ blob."""
    match = _NEXT_DATA_RE.search(html)
    if not match:
        raise ScraperError("Kakuyomu page is missing the __NEXT_DATA__ payload")
    try:
        data = json.loads(match.group(1))
        return data["props"]["pageProps"]["__APOLLO_STATE__"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ScraperError(f"Unable to read Kakuyomu Apollo state: {exc}") from exc


def parse_work_page(html: str, work_id: str) -> WorkPageData:
    """Parse a Kakuyomu work page into ordered episodes plus metadata.

    The authoritative, fully-ordered table of contents lives only in the embedded
    Apollo cache (the rendered DOM collapses most episodes), so everything is read
    from JSON. The cache also embeds unrelated recommended works, so the target work
    is resolved strictly via ROOT_QUERY keyed by ``work_id``.
    """
    apollo = _load_apollo_state(html)

    root = apollo.get("ROOT_QUERY", {})
    work_query_key = f'work({{"id":"{work_id}"}})'
    work_ref = root.get(work_query_key, {}).get("__ref")
    if not work_ref or work_ref not in apollo:
        raise ScraperError(f"Kakuyomu work {work_id} not found in page data")
    work = apollo[work_ref]

    episodes: list[tuple[str, str]] = []
    for chapter_ref in work.get("tableOfContentsV2") or []:
        if not isinstance(chapter_ref, dict):
            continue
        chapter = apollo.get(chapter_ref.get("__ref"), {})
        for union_ref in chapter.get("episodeUnions") or []:
            if not isinstance(union_ref, dict):
                continue
            episode = apollo.get(union_ref.get("__ref"))
            if isinstance(episode, dict) and episode.get("id"):
                episodes.append((episode["id"], episode.get("title") or ""))

    if not episodes:
        raise ScraperError(f"Kakuyomu work {work_id} has no episodes")

    return WorkPageData(
        work_id=work_id,
        title=(work.get("title") or work_id).strip(),
        episodes=episodes,
        author=_resolve_author(apollo, work),
        description=work.get("introduction") or work.get("catchphrase"),
        thumbnail_url=_resolve_thumbnail(work),
        genre=work.get("genre"),
        serial_status=work.get("serialStatus"),
        total_character_count=work.get("totalCharacterCount"),
    )


def _resolve_author(apollo: dict[str, Any], work: dict[str, Any]) -> str | None:
    ref = (work.get("author") or {}).get("__ref")
    account = apollo.get(ref) if ref else None
    if account:
        name = account.get("activityName") or account.get("name")
        if name:
            return name
    return work.get("alternateAuthorName")


def _resolve_thumbnail(work: dict[str, Any]) -> str | None:
    for key in ("ogImageUrl", "adminSquareImageUrl", "promotionalImageUrl", "adminCoverImageUrl"):
        value = work.get(key)
        if value:
            return value
    return None


def parse_chapter(html: str) -> tuple[str, str]:
    """Parse a Kakuyomu episode page into ``(title, normalized_text)``."""
    soup = BeautifulSoup(html, "lxml")

    title_node = soup.select_one(_EPISODE_TITLE_SELECTOR)
    if title_node is not None:
        remove_ruby_annotations(title_node)
    title = title_node.get_text(strip=True) if title_node else "Untitled"

    body_node = soup.select_one(_EPISODE_BODY_SELECTOR)
    if body_node is None:
        return title, ""
    remove_ruby_annotations(body_node)
    paragraphs = body_node.find_all("p", recursive=False) or body_node.find_all("p")
    lines = [p.get_text(separator="", strip=False) for p in paragraphs]
    body_text = "\n".join(lines) if lines else body_node.get_text(separator="\n", strip=False)
    return title, normalize_text(body_text)
