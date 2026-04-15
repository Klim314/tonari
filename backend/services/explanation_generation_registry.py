from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from typing import Any

logger = logging.getLogger(__name__)


class GenerationHandle:
    """In-flight generation for a single artifact.

    Holds the background task, all event subscribers, and a replay buffer of
    events already emitted this run so late subscribers can catch up without
    consulting the database.
    """

    def __init__(self) -> None:
        self.task: asyncio.Task[None] | None = None
        self.subscribers: set[asyncio.Queue[Any]] = set()
        # Bounded in practice by FACET_ORDER (~5 facet events plus one
        # terminal event per run). Revisit if a future producer emits
        # token-level events.
        self.buffer: list[Any] = []
        self.done: asyncio.Event = asyncio.Event()
        self.superseded: bool = False

    def emit(self, event: Any) -> None:
        self.buffer.append(event)
        for q in self.subscribers:
            q.put_nowait(event)

    def subscribe(self) -> asyncio.Queue[Any]:
        q: asyncio.Queue[Any] = asyncio.Queue()
        for ev in self.buffer:
            q.put_nowait(ev)
        if self.done.is_set():
            q.put_nowait(None)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[Any]) -> None:
        self.subscribers.discard(q)

    def close(self) -> None:
        """Signal to all subscribers that no more events will arrive."""
        for q in list(self.subscribers):
            q.put_nowait(None)
        self.done.set()


class GenerationRegistry:
    """Process-local registry of in-flight artifact generations.

    Keys are artifact IDs. Only one generation runs per artifact at a time; a
    regenerate request cancels the existing task and starts a fresh one.
    """

    def __init__(self) -> None:
        self._handles: dict[int, GenerationHandle] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get(self, artifact_id: int) -> GenerationHandle | None:
        async with self._lock:
            return self._handles.get(artifact_id)

    async def ensure(
        self,
        artifact_id: int,
        producer_factory: Callable[[], AsyncGenerator[Any, None]],
    ) -> GenerationHandle:
        """Return the running handle, or start a new one.

        Idempotent: if generation is already running for this artifact the
        existing handle is returned and ``producer_factory`` is not invoked.
        """
        async with self._lock:
            existing = self._handles.get(artifact_id)
            if existing is not None and not existing.done.is_set():
                return existing
            handle = GenerationHandle()
            self._handles[artifact_id] = handle

        async def runner() -> None:
            try:
                async for event in producer_factory():
                    handle.emit(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "generation task crashed",
                    extra={"artifact_id": artifact_id},
                )
            finally:
                handle.close()
                async with self._lock:
                    if self._handles.get(artifact_id) is handle:
                        del self._handles[artifact_id]

        handle.task = asyncio.create_task(runner())
        return handle

    async def cancel(
        self,
        artifact_id: int,
        *,
        emit_final: Any | None = None,
    ) -> None:
        """Cancel any running generation for ``artifact_id``.

        If ``emit_final`` is provided it is delivered to current subscribers
        before the task is cancelled, so they see a clean terminal event.
        """
        async with self._lock:
            handle = self._handles.get(artifact_id)
            if handle is not None:
                handle.superseded = True

        if handle is None:
            return

        if emit_final is not None:
            handle.emit(emit_final)

        if handle.task is not None and not handle.task.done():
            handle.task.cancel()

        try:
            await handle.done.wait()
        except asyncio.CancelledError:
            pass


_registry: GenerationRegistry | None = None


def get_registry() -> GenerationRegistry:
    global _registry
    if _registry is None:
        _registry = GenerationRegistry()
    return _registry
