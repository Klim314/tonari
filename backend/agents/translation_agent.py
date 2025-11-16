from __future__ import annotations

import logging
from functools import lru_cache
from typing import AsyncGenerator, List, Optional, Sequence

from agents.base_agent import BaseAgent, SegmentContext, SegmentContextInput
from agents.prompts import SYSTEM_DEFAULT
from app.config import settings

logger = logging.getLogger(__name__)


class TranslationAgent(BaseAgent):
    """Agent for JP→EN literary translation with preceding context support."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        api_base: str | None,
        chunk_chars: int,
        context_window: int,
        system_prompt: str | None = None,
    ) -> None:
        self.context_window = max(0, context_window)
        effective_prompt = system_prompt or SYSTEM_DEFAULT

        super().__init__(
            model=model,
            api_key=api_key,
            api_base=api_base,
            chunk_chars=chunk_chars,
            system_prompt=effective_prompt,
            human_message_template="{preceding_block}<source>\n{source_text}\n</source>\n\nReturn the translation only.",
        )

    async def stream_segment(
        self,
        text: str,
        *,
        preceding_segments: Optional[Sequence[SegmentContextInput]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream translation for a segment with preceding context.

        Args:
            text: Source text to translate.
            preceding_segments: Previous segments for context window.

        Yields:
            Translation text chunks.
        """
        cleaned = text.strip()
        if not cleaned:
            return

        preceding_block = self._render_preceding_block(preceding_segments)
        async for chunk in self.stream(
            source_text=cleaned,
            preceding_block=preceding_block,
        ):
            yield chunk

    async def translate_segment(
        self,
        text: str,
        *,
        preceding_segments: Optional[Sequence[SegmentContextInput]] = None,
    ) -> str:
        """Generate complete translation for a segment.

        Args:
            text: Source text to translate.
            preceding_segments: Previous segments for context window.

        Returns:
            Complete translated text.
        """
        collected: List[str] = []
        async for chunk in self.stream_segment(
            text, preceding_segments=preceding_segments
        ):
            collected.append(chunk)
        return "".join(collected).strip()

    def _render_preceding_block(
        self, preceding_segments: Optional[Sequence[SegmentContextInput]]
    ) -> str:
        """Render preceding segments as context block.

        Args:
            preceding_segments: Segments to include in context window.

        Returns:
            XML-formatted preceding block, or empty string if not applicable.
        """
        if self.context_window <= 0 or not preceding_segments:
            return ""

        normalized = self._normalize_context_segments(preceding_segments)
        if not normalized:
            return ""

        window = normalized[-self.context_window :]
        return self._render_block(window, block_name="preceding")


@lru_cache(maxsize=1)
def get_translation_agent() -> TranslationAgent:
    return TranslationAgent(
        model=settings.translation_model,
        api_key=settings.translation_api_key,
        api_base=settings.translation_api_base_url,
        chunk_chars=settings.translation_chunk_chars,
        context_window=settings.translation_context_segments,
    )


__all__ = [
    "TranslationAgent",
    "SegmentContext",
    "get_translation_agent",
]
