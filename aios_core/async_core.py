"""Async Core Wrappers — non-blocking access to sync AIOS services.

Uses ``asyncio.to_thread()`` to run synchronous Database, Orchestrator,
and KnowledgeGraph methods from async contexts without blocking the
Starlette event loop.

Provides AsyncDatabase, AsyncKnowledgeGraph, AsyncOrchestrator,
AsyncEventBusWrapper, and batch operation helpers.

Usage::

    from aios_core.async_core import AsyncDatabase
    db = AsyncDatabase("aios.sqlite")
    stats = await db.stats()
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

__all__ = [
    "AsyncDatabase",
    "AsyncEventBusWrapper",
    "AsyncKnowledgeGraph",
    "AsyncOrchestrator",
    "AsyncRunner",
    "async_batch",
    "async_parallel",
]


class AsyncRunner:
    """Mixin that delegates attribute access to a sync instance via to_thread."""

    _sync: Any

    async def _run(self, method_name: str, *args, **kwargs) -> Any:
        """Run ``self._sync.<method_name>(*args, **kwargs)`` in a thread."""
        method = getattr(self._sync, method_name)
        return await asyncio.to_thread(method, *args, **kwargs)

    async def _run_many(self, calls: Sequence[tuple]) -> list[Any]:
        """Execute multiple sync method calls concurrently.

        Each item in *calls* is ``(method_name, args, kwargs)``.
        """
        coros = [self._run(name, *a, **kw) for name, a, kw in calls]
        return list(await asyncio.gather(*coros, return_exceptions=True))


class AsyncDatabase(AsyncRunner):
    """Async wrapper around ``aios_core.storage.Database``."""

    def __init__(self, db_path: str = "aios.sqlite") -> None:
        """Initialize AsyncDatabase."""
        from aios_core.storage import Database

        self._sync = Database(db_path=db_path)

    # --- Explicitly-typed async shorthands ----------------------------------

    async def stats(self) -> dict:
        """Return database statistics."""
        return await self._run("stats")

    async def tables(self) -> list[str]:
        """Return list of table names."""
        return await self._run("tables")

    async def row_count(self, table: str) -> int:
        """Return row count for *table*."""
        return await self._run("row_count", table)

    async def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a read query."""
        return await self._run("query", sql, params)

    async def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Execute a read query returning one row."""
        return await self._run("query_one", sql, params)

    async def execute(self, sql: str, params: tuple = ()) -> Any:
        """Execute a write statement."""
        return await self._run("execute", sql, params)

    async def close(self) -> None:
        """Close the database connection."""
        await self._run("close")

    # --- Batch helpers ------------------------------------------------------

    async def batch_query(
        self, queries: Sequence[tuple[str, tuple]]
    ) -> list[list[dict]]:
        """Execute multiple queries concurrently.

        Each item is ``(sql, params)``.
        """
        calls = [("query", (sql, params), {}) for sql, params in queries]
        results = await self._run_many(calls)
        return results

    async def batch_execute(self, statements: Sequence[tuple[str, tuple]]) -> list[Any]:
        """Execute multiple write statements concurrently."""
        calls = [("execute", (sql, params), {}) for sql, params in statements]
        results = await self._run_many(calls)
        return results


class AsyncKnowledgeGraph(AsyncRunner):
    """Async wrapper around ``aios_core.knowledge_graph.KnowledgeGraph``."""

    def __init__(self) -> None:
        """Initialize AsyncKnowledgeGraph."""
        from aios_core.knowledge_graph import KnowledgeGraph

        self._sync = KnowledgeGraph()

    async def stats(self) -> dict:
        """stats."""
        return await self._run("stats")

    async def add_node(self, node_id: str, properties: dict) -> dict:
        """add node."""
        return await self._run("add_node", node_id, properties)

    async def add_edge(self, source: str, target: str, rel_type: str) -> dict | None:
        """add edge."""
        return await self._run("add_edge", source, target, rel_type)

    async def query_nodes(self, label: str = "") -> list[dict]:
        """Query nodes matching *label*."""
        return await self._run("query_nodes", label)

    async def shortest_path(self, source: str, target: str) -> list[str]:
        """Find shortest path between nodes."""
        return await self._run("shortest_path", source, target)

    async def batch_add_nodes(self, nodes: Sequence[tuple[str, dict]]) -> list[dict]:
        """Add multiple nodes concurrently."""
        calls = [("add_node", (nid, props), {}) for nid, props in nodes]
        results = await self._run_many(calls)
        return results


class AsyncOrchestrator(AsyncRunner):
    """Async wrapper around ``aios_core.orchestrator.Orchestrator``."""

    def __init__(self) -> None:
        """Initialize AsyncOrchestrator."""
        from aios_core.orchestrator import Orchestrator

        self._sync = Orchestrator()

    async def stats(self) -> dict:
        """Return orchestrator statistics."""
        return await self._run("stats")

    async def create_task(self, name: str, steps: list = []) -> dict:
        """Create a new task."""
        return await self._run("create_task", name, steps)

    async def run_task(self, task_id: str) -> dict:
        """Execute a task by ID."""
        return await self._run("run_task", task_id)

    async def list_tasks(self) -> list[dict]:
        """List all tasks."""
        return await self._run("list_tasks")


class AsyncEventBusWrapper(AsyncRunner):
    """Async wrapper around ``aios_core.event_bus.EventBus``."""

    def __init__(self) -> None:
        """Initialize AsyncEventBusWrapper."""
        from aios_core.event_bus import EventBus

        self._sync = EventBus()

    async def emit(self, event: str, source: str, payload: dict) -> None:
        """Emit an event synchronously in a thread."""
        await self._run("emit", event, source, payload)

    async def on(self, event: str, handler: Callable) -> None:
        """Register a handler (runs synchronously)."""
        await self._run("on", event, handler)

    async def stats(self) -> dict:
        """Return event bus statistics."""
        return await self._run("stats")


# ------------------------------------------------------------------
# Generic async helpers
# ------------------------------------------------------------------


async def async_batch(
    func: Callable, args_list: Sequence[tuple], kwargs_list: Sequence[dict] = ()
) -> list[Any]:
    """Run *func* for each ``(args, kwargs)`` pair concurrently via to_thread.

    Useful for any synchronous function that needs to be called many
    times without blocking the event loop.
    """
    coros = []
    for i, args in enumerate(args_list):
        kwargs = kwargs_list[i] if i < len(kwargs_list) else {}
        coros.append(asyncio.to_thread(func, *args, **kwargs))
    return list(await asyncio.gather(*coros, return_exceptions=True))


async def async_parallel(
    coros: Sequence[Awaitable],
    max_concurrent: int = 10,
) -> list[Any]:
    """Execute async coroutines with a concurrency limit.

    Uses a semaphore to cap concurrent execution, preventing
    resource exhaustion on large batch operations.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _guarded(c: Awaitable) -> Any:
        async with semaphore:
            return await c

    return list(
        await asyncio.gather(*(_guarded(c) for c in coros), return_exceptions=True)
    )
