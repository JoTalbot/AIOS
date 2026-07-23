"""Tests for memory manager search and storage."""

from aios_core.memory_manager import MemoryManager


def test_memory_manager_search_empty():
    mm = MemoryManager()
    results = mm.search(query="test", limit=5)
    assert isinstance(results, list)


def test_memory_manager_store():
    mm = MemoryManager()
    mm.store(content={"key": "value"}, owner="test_user")
    assert mm.stats() is not None
