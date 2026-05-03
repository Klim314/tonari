from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_openrouter import ChatOpenRouter

from observability import TraceContext, observed_span

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SegmentContext:
    src: str
    tgt: str


SegmentContextInput = SegmentContext | Mapping[str, Any]


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


def build_cached_system_messages(
    system_prompt: str,
    human_text: str,
) -> list[BaseMessage]:
    """Build messages with an Anthropic-style cache_control marker on the system prompt.

    The marker is a no-op below the provider's minimum cacheable size
    (1024 tok for Sonnet/Opus 4.x, 2048 tok for Haiku 4.5); leaving it in
    place is forward-compatible as prompts grow.
    """
    return [
        SystemMessage(
            content=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        ),
        HumanMessage(content=human_text),
    ]


def log_cache_usage(
    response_metadata: dict | None,
    usage_metadata: dict | None,
    *,
    provider: str,
    model: str,
) -> None:
    """Emit a structured log line with cache hit telemetry, when present."""
    if not response_metadata and not usage_metadata:
        return
    details = (usage_metadata or {}).get("input_token_details") or {}
    cache_read = details.get("cache_read") or details.get("cache_read_input_tokens")
    cache_create = details.get("cache_creation") or details.get("cache_creation_input_tokens")
    input_tokens = (usage_metadata or {}).get("input_tokens")
    if not (cache_read or cache_create):
        return
    logger.info(
        "LLM cache usage",
        extra={
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "cache_read_tokens": cache_read,
            "cache_creation_tokens": cache_create,
        },
    )


def _chunk_content_to_text(chunk_content) -> str:
    if isinstance(chunk_content, str):
        return chunk_content
    if isinstance(chunk_content, list):
        text_parts: list[str] = []
        for item in chunk_content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(str(item["text"]))
        return "".join(text_parts)
    return ""


def create_llm(
    provider: str,
    model: str,
    api_key: str,
    api_base: str | None,
) -> BaseChatModel:
    """Create the appropriate LLM based on the provider."""
    if provider == "openai":
        return ChatOpenAI(
            api_key=api_key,
            model=model,
            base_url=api_base or None,
            temperature=0.2,
            streaming=True,
            stream_usage=True,
        )
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model,
            temperature=0.2,
            streaming=True,
        )
    elif provider == "openrouter":
        return ChatOpenRouter(
            api_key=api_key,
            model=model,
            base_url=api_base or None,
            temperature=0.2,
            streaming=True,
            stream_usage=True,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def _normalize_context_segments(
    segments: Sequence[SegmentContextInput],
) -> list[SegmentContext]:
    normalized: list[SegmentContext] = []
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


def render_block(
    segments: Sequence[SegmentContextInput] | None,
    block_name: str = "preceding",
) -> str:
    """Render context segments as an XML block string."""
    if not segments:
        return ""

    normalized = _normalize_context_segments(segments)
    if not normalized:
        return ""

    lines: list[str] = [f"<{block_name}>"]
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
        self._llm: BaseChatModel | None = None
        self.prompt: ChatPromptTemplate | None = None

        if api_key:
            try:
                self._llm = create_llm(
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
            logger.info("API key missing; using stub")

    @property
    def has_provider(self) -> bool:
        return self._llm is not None and self.prompt is not None

    async def stream(
        self,
        *,
        trace: TraceContext | None = None,
        **format_kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream formatted messages through the LLM.

        Args:
            trace: Optional Langfuse trace context (name, session_id, user_id,
                metadata, tags). When omitted, the call is not observed.
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
            async for chunk in stub_stream(source_text, chunk_size=self.chunk_chars):
                yield chunk
            return

        messages = self.prompt.format_messages(**format_kwargs)
        if self.provider == "openrouter":
            system_text = next(
                (m.content for m in messages if isinstance(m, SystemMessage)), None
            )
            human_text = next(
                (m.content for m in messages if isinstance(m, HumanMessage)), None
            )
            if isinstance(system_text, str) and isinstance(human_text, str):
                messages = build_cached_system_messages(system_text, human_text)

        try:
            final_chunk = None
            with observed_span(trace, provider=self.provider, model=self.model) as config:
                stream_kwargs: dict[str, Any] = {}
                if config is not None:
                    stream_kwargs["config"] = config
                async for chunk in self._llm.astream(messages, **stream_kwargs):
                    final_chunk = chunk
                    delta = _chunk_content_to_text(chunk.content)
                    if delta:
                        yield delta
            if final_chunk is not None:
                log_cache_usage(
                    getattr(final_chunk, "response_metadata", None),
                    getattr(final_chunk, "usage_metadata", None),
                    provider=self.provider,
                    model=self.model,
                )
        except Exception:  # pragma: no cover
            logger.exception("Streaming failed")
            raise

    async def generate(
        self,
        *,
        trace: TraceContext | None = None,
        **format_kwargs,
    ) -> str:
        """Generate complete text by streaming and collecting all chunks.

        Args:
            trace: Optional Langfuse trace context.
            **format_kwargs: Arguments to format the prompt template with.

        Returns:
            Complete generated text.
        """
        collected: list[str] = []
        async for chunk in self.stream(trace=trace, **format_kwargs):
            collected.append(chunk)
        return "".join(collected).strip()



__all__ = [
    "BaseAgent",
    "SegmentContext",
    "SegmentContextInput",
    "TraceContext",
    "build_cached_system_messages",
    "create_llm",
    "log_cache_usage",
    "render_block",
    "stub_stream",
]
