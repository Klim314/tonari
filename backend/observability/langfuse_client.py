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


def build_runnable_config(
    trace: TraceContext | None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any] | None:
    """Build a LangChain RunnableConfig that the shared Langfuse handler reads.

    Per-call identifiers are passed via the reserved metadata keys
    (``langfuse_session_id``, ``langfuse_user_id``, ``langfuse_tags``) which
    Langfuse's langchain handler picks up to scope the trace correctly.

    ``provider`` and ``model`` are merged into metadata so cost/cache stats
    are attributable per-model in the Langfuse UI without callers having to
    duplicate that logic.

    Returns ``None`` when observability is disabled so callers can omit the
    ``config`` arg entirely.
    """
    handler = _get_shared_handler()
    if handler is None:
        return None

    metadata: dict[str, Any] = dict(trace.metadata) if trace and trace.metadata else {}
    if provider is not None:
        metadata.setdefault("provider", provider)
    if model is not None:
        metadata.setdefault("model", model)

    tags: list[str] = list(trace.tags) if trace and trace.tags else []
    if provider is not None and provider not in tags:
        tags.append(provider)

    if trace is not None:
        if trace.session_id:
            metadata["langfuse_session_id"] = trace.session_id
        if trace.user_id:
            metadata["langfuse_user_id"] = trace.user_id
        if tags:
            metadata["langfuse_tags"] = tags

    config: dict[str, Any] = {"callbacks": [handler]}
    if metadata:
        config["metadata"] = metadata
    if tags:
        config["tags"] = tags
    if trace is not None and trace.name:
        config["run_name"] = trace.name
    return config


def flush_langfuse() -> None:
    """Flush any buffered events. Safe to call when Langfuse is disabled."""
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        logger.warning("Langfuse flush failed", exc_info=True)
