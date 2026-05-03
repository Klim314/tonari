"""Langfuse integration for LLM observability.

Design:
  - One shared CallbackHandler per process (lazy-initialised). Per-call
    identifiers (session, user, tags, run name) flow through the LangChain
    runnable config's ``metadata`` dict using Langfuse's reserved keys
    (``langfuse_session_id`` etc.). This is the pattern the Langfuse 2.x
    langchain integration is built around — sharing the handler keeps all
    traces in one tree per session and avoids per-call construction overhead.
  - Process-wide ``Langfuse`` client used for shutdown flush.

When credentials are missing, every entry point returns ``None`` / no-ops.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_client_lock = Lock()
_client: Any | None = None
_client_init_failed = False

_handler_lock = Lock()
_handler: Any | None = None
_handler_init_failed = False


@dataclass(slots=True)
class TraceContext:
    """Identifiers and metadata for a single LLM call's trace.

    Populated by workflow code; passed to ``build_runnable_config`` to render
    into the LangChain runnable config that the shared Langfuse handler reads.
    """

    name: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


def get_langfuse_client():
    """Return the singleton Langfuse client, or None if disabled / unavailable."""
    global _client, _client_init_failed

    if _client is not None or _client_init_failed:
        return _client
    if not settings.langfuse_enabled:
        return None

    with _client_lock:
        if _client is not None or _client_init_failed:
            return _client
        try:
            from langfuse import Langfuse

            _client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            logger.info(
                "Langfuse initialised",
                extra={"host": settings.langfuse_host},
            )
        except Exception:
            _client_init_failed = True
            logger.warning("Failed to initialise Langfuse client", exc_info=True)
            return None
    return _client


def _get_shared_handler():
    """Return the process-wide CallbackHandler, or None if disabled.

    Per-call identifiers must NOT be baked into this handler — pass them via
    the runnable config's ``metadata`` (see ``build_runnable_config``).
    """
    global _handler, _handler_init_failed

    if _handler is not None or _handler_init_failed:
        return _handler
    if not settings.langfuse_enabled:
        return None
    if get_langfuse_client() is None:
        return None

    with _handler_lock:
        if _handler is not None or _handler_init_failed:
            return _handler
        try:
            # Langfuse 3.x: handler picks up the global client initialised by
            # get_langfuse_client() above; no per-handler credentials needed.
            from langfuse.langchain import CallbackHandler

            _handler = CallbackHandler()
        except Exception:
            _handler_init_failed = True
            logger.warning("Failed to construct Langfuse CallbackHandler", exc_info=True)
            return None
    return _handler


@contextmanager
def observed_span(
    trace: TraceContext | None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> Iterator[dict[str, Any] | None]:
    """Open a Langfuse parent span and yield the LangChain runnable config.

    In Langfuse 3.x the langchain ``CallbackHandler`` attaches to the current
    OTel span — without an enclosing parent span, the handler produces no
    output. This context manager opens that parent span via the Langfuse
    client, applies session/user/tags via ``span.update_trace(...)``, and
    yields a runnable config carrying the handler that the LLM invocation
    should pass to ``astream``/``ainvoke``.

    Yields ``None`` when observability is disabled so callers can skip the
    ``config`` arg entirely.
    """
    client = get_langfuse_client()
    handler = _get_shared_handler()
    if client is None or handler is None:
        yield None
        return

    span_name = (trace.name if trace and trace.name else None) or "llm-call"

    metadata: dict[str, Any] = dict(trace.metadata) if trace and trace.metadata else {}
    if provider is not None:
        metadata.setdefault("provider", provider)
    if model is not None:
        metadata.setdefault("model", model)

    tags: list[str] = list(trace.tags) if trace and trace.tags else []
    if provider is not None and provider not in tags:
        tags.append(provider)

    # Force a fresh root trace per call. Without this, Langfuse v3's
    # start_as_current_span nests under the current OTel span — so a
    # workflow that processes N items in one async task would collapse all
    # N LLM calls into one trace tree instead of producing N traces grouped
    # by session.
    try:
        trace_id = client.create_trace_id()
        span_cm = client.start_as_current_span(
            name=span_name,
            trace_context={"trace_id": trace_id},
        )
    except Exception:
        logger.warning("Failed to open Langfuse parent span", exc_info=True)
        yield None
        return

    with span_cm as span:
        update_kwargs: dict[str, Any] = {}
        if metadata:
            update_kwargs["metadata"] = metadata
        if tags:
            update_kwargs["tags"] = tags
        if trace is not None and trace.session_id:
            update_kwargs["session_id"] = trace.session_id
        if trace is not None and trace.user_id:
            update_kwargs["user_id"] = trace.user_id
        if update_kwargs:
            try:
                span.update_trace(**update_kwargs)
            except Exception:
                logger.warning("Failed to update Langfuse trace", exc_info=True)

        yield {"callbacks": [handler]}


def build_runnable_config(
    trace: TraceContext | None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any] | None:
    """Deprecated thin shim — prefer ``observed_span``.

    Kept temporarily so call sites can migrate without ripple. Returns a
    config attached to the *current* span context only; without an enclosing
    ``observed_span``, the v3 handler produces nothing.
    """
    handler = _get_shared_handler()
    if handler is None:
        return None
    return {"callbacks": [handler]}


def flush_langfuse() -> None:
    """Flush any buffered events. Safe to call when Langfuse is disabled."""
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        logger.warning("Langfuse flush failed", exc_info=True)
