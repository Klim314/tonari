from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, List, Mapping, Optional, Sequence, Union

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

logger = logging.getLogger(__name__)


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


def stub_stream(src: str, *, chunk_size: int = 24) -> AsyncGenerator[str, None]:
    """Placeholder stub that emits lorem ipsum proportionate to src length."""

    async def _stream():
        lorem = build_lorem_text(max(len(src.strip()), 16))
        for idx in range(0, len(lorem), chunk_size):
            await asyncio.sleep(0.05)
            yield lorem[idx : idx + chunk_size]

    return _stream()


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


class BaseAgent:
    """Base agent for LLM-powered text generation with streaming support."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        api_base: str | None,
        chunk_chars: int,
        system_prompt: str,
        human_message_template: str,
        provider: str = "openai",
    ) -> None:
        self.model = model
        self.chunk_chars = max(8, chunk_chars)
        self._api_key = api_key
        self.provider = provider
        self._llm: Optional[BaseChatModel] = None
        self.prompt: Optional[ChatPromptTemplate] = None

        if api_key and ChatPromptTemplate:
            try:
                self._llm = self._create_llm(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    api_base=api_base,
                )
                self.prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", system_prompt),
                        ("human", human_message_template),
                    ]
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM for provider {provider}: {e}")
                logger.info("Using stub instead")
        else:
            logger.info(
                "LangChain dependencies unavailable or API key missing; using stub"
            )

    @staticmethod
    def _create_llm(
        provider: str,
        model: str,
        api_key: str,
        api_base: str | None,
    ) -> BaseChatModel:
        """Create the appropriate LLM based on the provider."""
        if provider == "openai":
            if ChatOpenAI is None:
                raise ImportError("langchain-openai not installed")
            return ChatOpenAI(
                api_key=api_key,
                model=model,
                base_url=api_base or None,
                temperature=0.2,
                streaming=True,
            )
        elif provider == "gemini":
            if ChatGoogleGenerativeAI is None:
                raise ImportError("langchain-google-genai not installed")
            return ChatGoogleGenerativeAI(
                google_api_key=api_key,
                model=model,
                temperature=0.2,
                streaming=True,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @property
    def has_provider(self) -> bool:
        return self._llm is not None and self.prompt is not None

    async def stream(
        self,
        **format_kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream formatted messages through the LLM.

        Args:
            **format_kwargs: Arguments to format the prompt template with.
                Must include all variables from system and human message templates.

        Yields:
            Text chunks from the LLM or stub.
        """
        # Extract source text for stub fallback
        source_text = format_kwargs.get("source_text", "")

        if not source_text:
            return

        if not self._llm or not self.prompt:
            async for chunk in stub_stream(
                source_text, chunk_size=self.chunk_chars
            ):
                yield chunk
            return

        messages: List[BaseMessage] = self.prompt.format_messages(**format_kwargs)
        try:
            async for chunk in self._llm.astream(messages):
                delta = _chunk_content_to_text(chunk.content)
                if delta:
                    yield delta
        except Exception:  # pragma: no cover
            logger.exception("Streaming failed")
            raise

    async def generate(
        self,
        **format_kwargs,
    ) -> str:
        """Generate complete text by streaming and collecting all chunks.

        Args:
            **format_kwargs: Arguments to format the prompt template with.

        Returns:
            Complete generated text.
        """
        collected: List[str] = []
        async for chunk in self.stream(**format_kwargs):
            collected.append(chunk)
        return "".join(collected).strip()

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

    @staticmethod
    def _render_block(
        segments: Optional[Sequence[SegmentContextInput]],
        block_name: str = "preceding",
    ) -> str:
        """Render context segments as XML block.

        Args:
            segments: Sequence of segments to render.
            block_name: Name of the block (e.g., "preceding", "following").

        Returns:
            XML-formatted block string, or empty string if no segments.
        """
        if not segments:
            return ""

        normalized = BaseAgent._normalize_context_segments(segments)
        if not normalized:
            return ""

        lines: List[str] = [f"<{block_name}>"]
        for segment in normalized:
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
        lines.append(f"</{block_name}>\n")
        return "\n".join(lines)


__all__ = [
    "BaseAgent",
    "SegmentContext",
    "SegmentContextInput",
    "stub_stream",
]
