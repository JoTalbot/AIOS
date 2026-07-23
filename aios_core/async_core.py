"""Async Core Wrappers — non-blocking access to sync AIOS services.

Uses ``asyncio.to_thread()`` to run synchronous Database, Orchestrator,
and KnowledgeGraph methods from async contexts without blocking the
Starlette event loop.

Usage::

    from aios_core.async_core import AsyncDatabase
    db = AsyncDatabase("aios.sqlite")
    stats = await db.stats()
"""

from __future__ import annotations

import asyncio
from typing import Any


class AsyncRunner:
    """Mixin that delegates attribute access to a sync instance via to_thread."""

    _sync: Any

    async def _run(self, method_name: str, *args, **kwargs) -> Any:
        """Run ``self._sync.<method_name>(*args, **kwargs)`` in a thread."""
        method = getattr(self._sync, method_name)
        return await asyncio.to_thread(method, *args, **kwargs)


class AsyncDatabase(AsyncRunner):
    """Async wrapper around ``aios_core.storage.Database``."""

    def __init__(self, db_path: str = "aios.sqlite") -> None:
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


class AsyncKnowledgeGraph(AsyncRunner):
    """Async wrapper around ``aios_core.knowledge_graph.KnowledgeGraph``."""

    def __init__(self) -> None:
        from aios_core.knowledge_graph import KnowledgeGraph

        self._sync = KnowledgeGraph()

    async def stats(self) -> dict:
        return await self._run("stats")

    async def add_node(self, node_id: str, properties: dict) -> dict:
        return await self._run("add_node", node_id, properties)

    async def add_edge(self, source: str, target: str, rel_type: str) -> dict | None:
        return await self._run("add_edge", source, target, rel_type)
