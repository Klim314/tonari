from __future__ import annotations

import logging
from functools import lru_cache
from typing import AsyncGenerator, List, Optional, Sequence

from agents.base_agent import BaseAgent, SegmentContext, SegmentContextInput
from agents.prompts import SYSTEM_EXPLANATION
from app.config import settings
from constants.llm import get_model_info

logger = logging.getLogger(__name__)


class ExplanationAgent(BaseAgent):
    """Agent for explaining translation choices with surrounding context."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        api_base: str | None,
        chunk_chars: int,
        provider: str = "openai",
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            api_base=api_base,
            chunk_chars=chunk_chars,
            system_prompt=SYSTEM_EXPLANATION,
            human_message_template="{context_block}\n\nProvide a markdown explanation of how this translation was made.",
            provider=provider,
        )

    async def stream_explanation(
        self,
        current_source: str,
        current_translation: str,
        *,
        preceding_segments: Optional[Sequence[SegmentContextInput]] = None,
        following_segments: Optional[Sequence[SegmentContextInput]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream explanation for a translation with surrounding context.

        Args:
            current_source: Source text of the segment being explained.
            current_translation: Translation of the segment being explained.
            preceding_segments: Segments before the current one for context.
            following_segments: Segments after the current one for context.

        Yields:
            Explanation markdown chunks.
        """
        context_block = self._render_context_block(
            preceding_segments, current_source, current_translation, following_segments
        )

        if not context_block:
            return

        async for chunk in self.stream(source_text=current_source, context_block=context_block):
            yield chunk

    async def generate_explanation(
        self,
        current_source: str,
        current_translation: str,
        *,
        preceding_segments: Optional[Sequence[SegmentContextInput]] = None,
        following_segments: Optional[Sequence[SegmentContextInput]] = None,
    ) -> str:
        """Generate complete explanation for a translation.

        Args:
            current_source: Source text of the segment being explained.
            current_translation: Translation of the segment being explained.
            preceding_segments: Segments before the current one for context.
            following_segments: Segments after the current one for context.

        Returns:
            Complete explanation markdown text.
        """
        collected: List[str] = []
        async for chunk in self.stream_explanation(
            current_source,
            current_translation,
            preceding_segments=preceding_segments,
            following_segments=following_segments,
        ):
            collected.append(chunk)
        return "".join(collected).strip()

    @staticmethod
    def _render_context_block(
        preceding_segments: Optional[Sequence[SegmentContextInput]],
        current_source: str,
        current_translation: str,
        following_segments: Optional[Sequence[SegmentContextInput]],
    ) -> str:
        """Render current and surrounding segments as context block.

        Args:
            preceding_segments: Segments before current.
            current_source: Source of current segment.
            current_translation: Translation of current segment.
            following_segments: Segments after current.

        Returns:
            XML-formatted context block.
        """
        lines: List[str] = []

        # Add preceding context
        if preceding_segments:
            preceding_block = BaseAgent._render_block(
                preceding_segments, block_name="preceding"
            )
            if preceding_block:
                lines.append(preceding_block)

        # Add current segment (highlighted)
        if current_source and current_translation:
            lines.append("<current>")
            lines.append("<source>")
            lines.append(current_source)
            lines.append("</source>")
            lines.append("<translation>")
            lines.append(current_translation)
            lines.append("</translation>")
            lines.append("</current>\n")

        # Add following context
        if following_segments:
            following_block = BaseAgent._render_block(
                following_segments, block_name="following"
            )
            if following_block:
                lines.append(following_block)

        return "\n".join(lines)


@lru_cache(maxsize=1)
def get_explanation_agent() -> ExplanationAgent:
    # Get model info to determine provider
    model_info = get_model_info(settings.translation_model)
    provider = model_info.provider if model_info else "openai"

    # Get the appropriate API key for the provider
    api_key = settings.get_api_key_for_provider(provider)

    return ExplanationAgent(
        model=settings.translation_model,
        api_key=api_key,
        api_base=settings.translation_api_base_url,
        chunk_chars=settings.translation_chunk_chars,
        provider=provider,
    )


__all__ = [
    "ExplanationAgent",
    "get_explanation_agent",
]
