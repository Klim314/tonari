from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Sequence
from functools import lru_cache

from agents.base_agent import BaseAgent, SegmentContext, SegmentContextInput
from agents.prompts import SYSTEM_DEFAULT
from app.config import settings
from constants.llm import get_model_info

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
        provider: str = "openai",
    ) -> None:
        self.context_window = max(0, context_window)
        effective_prompt = system_prompt or SYSTEM_DEFAULT

        super().__init__(
            model=model,
            api_key=api_key,
            api_base=api_base,
            chunk_chars=chunk_chars,
            system_prompt=effective_prompt,
            human_message_template=(
                "{preceding_block}<source>\n{source_text}\n</source>"
                "{instruction_block}\n\nReturn the translation only."
            ),
            provider=provider,
        )

    async def stream_segment(
        self,
        text: str,
        *,
        preceding_segments: Sequence[SegmentContextInput] | None = None,
        instruction: str | None = None,
        current_translation: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream translation for a segment with preceding context.

        Args:
            text: Source text to translate.
            preceding_segments: Previous segments for context window.
            instruction: Optional user instruction to guide the retranslation
                (e.g., "make it more casual", "keep the honorific").
            current_translation: The existing translation to improve upon.
                Required when instruction is provided.

        Yields:
            Translation text chunks.
        """
        cleaned = text.strip()
        if not cleaned:
            return

        logger.info(
            "TranslationAgent stream_segment",
            extra={
                "model": self.model,
                "provider": self.provider,
                "preceding_count": len(preceding_segments or []),
                "source_preview": cleaned[:80] + "..." if len(cleaned) > 80 else cleaned,
                "has_instruction": instruction is not None,
                "has_current_translation": current_translation is not None,
            },
        )

        preceding_block = self._render_preceding_block(preceding_segments)
        instruction_block = self._render_instruction_block(instruction, current_translation)
        async for chunk in self.stream(
            source_text=cleaned,
            preceding_block=preceding_block,
            instruction_block=instruction_block,
        ):
            yield chunk

    async def translate_segment(
        self,
        text: str,
        *,
        preceding_segments: Sequence[SegmentContextInput] | None = None,
    ) -> str:
        """Generate complete translation for a segment.

        Args:
            text: Source text to translate.
            preceding_segments: Previous segments for context window.

        Returns:
            Complete translated text.
        """
        collected: list[str] = []
        async for chunk in self.stream_segment(text, preceding_segments=preceding_segments):
            collected.append(chunk)
        return "".join(collected).strip()

    def _render_preceding_block(
        self, preceding_segments: Sequence[SegmentContextInput] | None
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

    def _render_instruction_block(
        self, instruction: str | None, current_translation: str | None = None
    ) -> str:
        """Render instruction block for guided retranslation.

        Args:
            instruction: User-provided instruction for the retranslation.
            current_translation: The existing translation to improve upon.

        Returns:
            XML-formatted block with current translation and instruction,
            or empty string if no instruction.
        """
        if not instruction or not instruction.strip():
            return ""

        parts = []

        # Include the current translation so the model knows what to improve
        if current_translation and current_translation.strip():
            parts.append(
                f"<current_translation>\n{current_translation.strip()}\n</current_translation>"
            )

        parts.append(f"<instruction>\n{instruction.strip()}\n</instruction>")

        return "\n\n" + "\n\n".join(parts)


@lru_cache(maxsize=1)
def get_translation_agent() -> TranslationAgent:
    # Get model info to determine provider
    model_info = get_model_info(settings.translation_model)
    provider = model_info.provider if model_info else "openai"

    # Get the appropriate API key for the provider
    api_key = settings.get_api_key_for_provider(provider)

    return TranslationAgent(
        model=settings.translation_model,
        api_key=api_key,
        api_base=settings.translation_api_base_url,
        chunk_chars=settings.translation_chunk_chars,
        context_window=settings.translation_context_segments,
        provider=provider,
    )


__all__ = [
    "TranslationAgent",
    "SegmentContext",
    "get_translation_agent",
]
