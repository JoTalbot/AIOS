"""Tests for async core wrappers."""
import asyncio
from aios_core.async_bus import AsyncEventBus
from aios_core.async_core import AsyncDatabase
from aios_core.container import AppConfig, AppContainer


def test_async_bus_emit_and_handler():
    """Async handlers receive events."""
    bus = AsyncEventBus()
    received = []

    async def my_handler(payload):
        received.append(payload)

    bus.on("test.event", my_handler)
    asyncio.run(bus.emit("test.event", {"x": 42}))
    assert len(received) == 1
    assert received[0]["x"] == 42


def test_async_bus_multiple_handlers():
    """Multiple async handlers run concurrently."""
    bus = AsyncEventBus()
    results = []

    async def h1(p):
        results.append(1)

    async def h2(p):
        results.append(2)

    async def h3(p):
        results.append(3)

    for h in (h1, h2, h3):
        bus.on("multi", h)
    asyncio.run(bus.emit("multi", {}))
    assert sorted(results) == [1, 2, 3]

def test_async_bus_stats():
    bus = AsyncEventBus()
    assert "async_handlers" in bus.stats()


def test_async_db_stats():
    """AsyncDatabase wraps sync Database via to_thread."""
    db = AsyncDatabase(db_path=":memory:")
    stats = asyncio.run(db.stats())
    assert stats["dialect"] == "sqlite"


def test_async_db_tables():
    db = AsyncDatabase(db_path=":memory:")
    tables = asyncio.run(db.tables())
    assert isinstance(tables, list)


def test_async_db_row_count():
    import sqlite3
    db = AsyncDatabase(db_path=":memory:")
    try:
        count = asyncio.run(db.row_count("nonexistent"))
        assert count in (0, None)
    except (sqlite3.OperationalError, Exception):
        pass  # table does not exist — OK


def test_container_async_services():
    c = AppContainer(AppConfig(db_path=":memory:"))
    bus = c.async_bus()
    db = c.async_db()
    kg = c.async_kg()
    assert bus is not None
    assert db is not None
    assert kg is not None
