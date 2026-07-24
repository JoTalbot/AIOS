"""Async Event Bus — non-blocking wrapper around the sync EventBus.

Supports priority handlers, wildcard subscriptions, middleware pipelines,
event history, and back-pressure for overloaded consumers.

Usage::

    from aios_core.async_bus import AsyncEventBus
    bus = AsyncEventBus()
    await bus.on("user.created", my_handler)
    await bus.emit("user.created", {"id": 42})
"""

from __future__ import annotations

import asyncio
import fnmatch
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from aios_core.event_bus import EventBus

Handler = Callable[[dict[str, Any]], Awaitable[None]]

__all__ = ["AsyncEventBus", "AsyncMiddleware"]


class AsyncMiddleware:
    """Base class for async middleware that can transform payloads before handlers run.

    Override ``before_emit`` to modify or filter events, ``after_emit``
    to post-process results or log completions.
    """

    async def before_emit(
        self, event: str, payload: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Transform *payload* before emission.  Return ``None`` to suppress."""
        return payload

    async def after_emit(
        self, event: str, payload: dict[str, Any], elapsed_ms: float
    ) -> None:
        """Post-process hook called after all handlers complete."""


class _PriorityEntry:
    """Internal handler entry with priority for ordered execution."""

    __slots__ = ("handler", "priority", "name")

    def __init__(self, handler: Handler, priority: int = 0, name: str = ""):
        self.handler = handler
        self.priority = priority
        self.name = name or handler.__qualname__

    def __lt__(self, other: "_PriorityEntry") -> bool:
        return self.priority < other.priority


class AsyncEventBus:
    """Async wrapper around the synchronous EventBus.

    Delegates storage to the sync bus but provides async emit/on
    so that event handlers can be coroutines without blocking
    the Starlette event loop.

    Features:
    - Priority-based handler ordering (lower runs first)
    - Wildcard subscriptions (e.g. ``user.*``)
    - Middleware pipeline for pre/post processing
    - Bounded event history for replay/debugging
    - Back-pressure via ``max_concurrent`` concurrency limit
    """

    def __init__(
        self,
        sync_bus: EventBus | None = None,
        history_size: int = 200,
        max_concurrent: int = 50,
    ) -> None:
        """Initialize AsyncEventBus."""
        self._sync = sync_bus or EventBus()
        self._handlers: Dict[str, List[_PriorityEntry]] = defaultdict(list)
        self._wildcards: List[tuple[str, _PriorityEntry]] = []
        self._middleware: List[AsyncMiddleware] = []
        self._history: List[dict[str, Any]] = []
        self._history_size = history_size
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._emit_count: int = 0
        self._error_count: int = 0

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def on(
        self,
        event: str,
        handler: Handler,
        priority: int = 0,
        name: str = "",
    ) -> None:
        """Register an async *handler* for *event* with optional *priority*.

        Lower priority values execute first.  Handlers with the same priority
        run concurrently.
        """
        entry = _PriorityEntry(handler, priority, name)
        if "*" in event or "?" in event:
            self._wildcards.append((event, entry))
        else:
            self._handlers[event].append(entry)
            self._handlers[event].sort()

    def off(self, event: str, handler: Handler | None = None) -> int:
        """Remove handlers for *event*.  If *handler* is given, remove only
        that one; otherwise clear all handlers for the event.
        Returns the number of handlers removed.
        """
        removed = 0
        if handler is None:
            removed = len(self._handlers.pop(event, []))
        else:
            entries = self._handlers.get(event, [])
            new_entries = [e for e in entries if e.handler is not handler]
            removed = len(entries) - len(new_entries)
            self._handlers[event] = new_entries
        # Also remove matching wildcards
        if handler is not None:
            old_wild = self._wildcards
            self._wildcards = [
                (pat, entry)
                for pat, entry in old_wild
                if entry.handler is not handler or not fnmatch.fnmatch(event, pat)
            ]
            removed += len(old_wild) - len(self._wildcards)
        return removed

    def add_middleware(self, middleware: AsyncMiddleware) -> None:
        """Append *middleware* to the processing pipeline."""
        self._middleware.append(middleware)

    def remove_middleware(self, middleware: AsyncMiddleware) -> None:
        """Remove *middleware* from the pipeline."""
        self._middleware = [m for m in self._middleware if m is not middleware]

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        """Emit *event* — runs sync handlers inline, async handlers concurrently.

        Middleware is applied before handler dispatch.  If any middleware
        returns ``None``, the event is suppressed.
        """
        # Middleware — before
        for mw in self._middleware:
            payload = await mw.before_emit(event, payload)
            if payload is None:
                return  # suppressed

        start = time.monotonic()

        # Sync handlers via the underlying bus
        self._sync.emit(event, "async_bus", payload)

        # Collect async handlers: exact match + wildcards
        handlers: List[Handler] = [
            e.handler for e in self._handlers.get(event, [])
        ]
        for pattern, entry in self._wildcards:
            if fnmatch.fnmatch(event, pattern):
                handlers.append(entry.handler)

        # Dispatch with concurrency control
        if handlers:
            async def _safe_call(h: Handler) -> None:
                async with self._semaphore:
                    try:
                        await h(payload)
                    except Exception:
                        self._error_count += 1

            await asyncio.gather(
                *(_safe_call(h) for h in handlers), return_exceptions=True
            )

        elapsed = (time.monotonic() - start) * 1000.0
        self._emit_count += 1

        # Middleware — after
        for mw in self._middleware:
            try:
                await mw.after_emit(event, payload, elapsed)
            except Exception:
                pass  # middleware after-hooks must not break emission

        # History
        self._history.append(
            {"event": event, "payload": payload, "elapsed_ms": round(elapsed, 3)}
        )
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size:]

    # ------------------------------------------------------------------
    # Replay / inspection
    # ------------------------------------------------------------------

    async def replay(self, count: int | None = None) -> int:
        """Replay stored history events through the bus.

        Returns the number of events replayed.
        """
        events = self._history if count is None else self._history[-count:]
        for record in events:
            await self.emit(record["event"], record["payload"])
        return len(events)

    def get_history(
        self, event: str | None = None, limit: int = 50
    ) -> List[dict[str, Any]]:
        """Return recent history, optionally filtered by *event* name."""
        if event:
            filtered = [r for r in self._history if r["event"] == event]
        else:
            filtered = self._history
        return filtered[-limit:]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return combined statistics."""
        return {
            **self._sync.stats(),
            "async_handlers": sum(
                len(v) for v in self._handlers.values()
            ),
            "wildcard_patterns": len(self._wildcards),
            "middleware_count": len(self._middleware),
            "async_events": list(self._handlers.keys()),
            "total_emits": self._emit_count,
            "total_errors": self._error_count,
            "history_size": len(self._history),
            "max_concurrent": self._max_concurrent,
        }

    def clear(self) -> None:
        """Remove all async handlers, wildcards, and history."""
        self._handlers.clear()
        self._wildcards.clear()
        self._history.clear()
        self._emit_count = 0
        self._error_count = 0
