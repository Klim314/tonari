from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, AsyncGenerator, List, Mapping, Optional, Sequence, Union

from agents.prompts import SYSTEM_DEFAULT
from app.config import settings

logger = logging.getLogger(__name__)

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


@dataclass(slots=True)
class SegmentContext:
    src: str
    tgt: str


SegmentContextInput = Union[SegmentContext, Mapping[str, Any]]


LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. Suspendisse "
    "lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed, dolor."
)


def build_lorem_text(min_chars: int) -> str:
    if min_chars <= 0:
        return ""
    repeats = (min_chars // len(LOREM)) + 1
    text = (LOREM + " ") * repeats
    return text[:min_chars].strip()


def stub_translate(src: str) -> str:
    """Placeholder translation that emits lorem ipsum proportionate to src length."""

    return build_lorem_text(max(len(src.strip()), 16))


async def stream_lorem_translation(src: str, *, chunk_size: int = 24) -> AsyncGenerator[str, None]:
    lorem = stub_translate(src)
    for idx in range(0, len(lorem), chunk_size):
        await asyncio.sleep(0.05)
        yield lorem[idx : idx + chunk_size]


def _chunk_content_to_text(chunk_content) -> str:
    if isinstance(chunk_content, str):
        return chunk_content
    if isinstance(chunk_content, list):
        text_parts: List[str] = []
        for item in chunk_content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(str(item["text"]))
        return "".join(text_parts)
    return ""


class TranslationAgent:
    """Lightweight agent wrapper around LangChain ChatOpenAI for JP→EN translation."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        api_base: str | None,
        chunk_chars: int,
        context_window: int,
    ) -> None:
        self.chunk_chars = max(8, chunk_chars)
        self.context_window = max(0, context_window)
        self._api_key = api_key
        self._llm: Optional[ChatOpenAI] = None
        self.prompt: Optional[ChatPromptTemplate] = None
        if api_key and ChatOpenAI and ChatPromptTemplate:
            self._llm = ChatOpenAI(
                api_key=api_key,
                model=model,
                base_url=api_base or None,
                temperature=0.2,
                streaming=True,
            )
            self.prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        SYSTEM_DEFAULT,
                    ),
                    (
                        "human",
                        "{preceding_block}<source>\n{source_text}\n</source>\n\nReturn the translation only.",
                    ),
                ]
            )
        else:
            logger.info("LangChain dependencies unavailable or API key missing; using lorem stub")

    @property
    def has_provider(self) -> bool:
        return self._llm is not None and self.prompt is not None

    async def stream_segment(
        self,
        text: str,
        *,
        preceding_segments: Optional[Sequence[SegmentContextInput]] = None,
    ) -> AsyncGenerator[str, None]:
        cleaned = text.strip()
        if not cleaned:
            return
        if not self._llm or not self.prompt:
            async for chunk in stream_lorem_translation(cleaned, chunk_size=self.chunk_chars):
                yield chunk
            return
        preceding_block = self._render_preceding_block(preceding_segments)
        messages: List[BaseMessage] = self.prompt.format_messages(
            source_text=cleaned,
            preceding_block=preceding_block,
        )
        try:
            async for chunk in self._llm.astream(messages):
                delta = _chunk_content_to_text(chunk.content)
                if delta:
                    yield delta
        except Exception:  # pragma: no cover
            logger.exception("Translation streaming failed")
            raise

    async def translate_segment(
        self,
        text: str,
        *,
        preceding_segments: Optional[Sequence[SegmentContextInput]] = None,
    ) -> str:
        collected: List[str] = []
        async for chunk in self.stream_segment(text, preceding_segments=preceding_segments):
            collected.append(chunk)
        return "".join(collected).strip()

    def _render_preceding_block(
        self, preceding_segments: Optional[Sequence[SegmentContextInput]]
    ) -> str:
        if self.context_window <= 0 or not preceding_segments:
            return ""
        normalized = self._normalize_context_segments(preceding_segments)
        if not normalized:
            return ""
        window = normalized[-self.context_window :]
        lines: List[str] = ["<preceding>"]
        for segment in window:
            if not segment.src and not segment.tgt:
                continue
            lines.append("<segment>")
            if segment.src:
                lines.append("<source>")
                lines.append(segment.src)
                lines.append("</source>")
            if segment.tgt:
                lines.append("<translation>")
                lines.append(segment.tgt)
                lines.append("</translation>")
            lines.append("</segment>")
        lines.append("</preceding>\n\n")
        return "\n".join(lines)

    @staticmethod
    def _normalize_context_segments(
        segments: Sequence[SegmentContextInput],
    ) -> List[SegmentContext]:
        normalized: List[SegmentContext] = []
        for raw in segments:
            if isinstance(raw, SegmentContext):
                normalized.append(raw)
                continue
            if isinstance(raw, Mapping):
                src_value = raw.get("src") or raw.get("source") or ""
                tgt_value = raw.get("tgt") or raw.get("translation") or ""
                src = str(src_value).strip()
                tgt = str(tgt_value).strip()
                if not src and not tgt:
                    continue
                normalized.append(SegmentContext(src=src, tgt=tgt))
        return normalized


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
    "stream_lorem_translation",
]
