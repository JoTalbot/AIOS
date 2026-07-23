"""Async Event Bus — non-blocking wrapper around the sync EventBus.

Usage::

    from aios_core.async_bus import AsyncEventBus
    bus = AsyncEventBus()
    await bus.on("user.created", my_handler)
    await bus.emit("user.created", {"id": 42})
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List

from aios_core.event_bus import EventBus

Handler = Callable[[dict[str, Any]], Awaitable[None]]


class AsyncEventBus:
    """Async wrapper around the synchronous EventBus.

    Delegates storage to the sync bus but provides async emit/on
    so that event handlers can be coroutines without blocking
    the Starlette event loop.
    """

    def __init__(self, sync_bus: EventBus | None = None) -> None:
        self._sync = sync_bus or EventBus()
        self._async_handlers: Dict[str, List[Handler]] = {}

    def on(self, event: str, handler: Handler) -> None:
        """Register an async *handler* for *event*."""
        self._async_handlers.setdefault(event, []).append(handler)

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        """Emit *event* — runs sync handlers inline, async handlers concurrently."""
        # Sync handlers via the underlying bus
        self._sync.emit(event, 'async_bus', payload)

        # Async handlers run concurrently
        handlers = self._async_handlers.get(event, [])
        if handlers:
            await asyncio.gather(*(h(payload) for h in handlers), return_exceptions=True)

    def stats(self) -> dict:
        """Return combined statistics."""
        return {
            **self._sync.stats(),
            "async_handlers": sum(len(v) for v in self._async_handlers.values()),
            "async_events": list(self._async_handlers.keys()),
        }
