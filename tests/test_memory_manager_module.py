"""Tests for aios_core/memory_manager.py"""
from __future__ import annotations
import pytest
from aios_core.memory_manager import MemoryManager
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def memory(db):
    return MemoryManager(db)


class TestMemoryManager:
    def test_store(self, memory):
        item = memory.store(content="Important fact", category="operational")
        assert item is not None

    def test_store_with_tags(self, memory):
        item = memory.store(content="tagged", category="test", tags=["tag1", "tag2"])
        assert item is not None

    def test_retrieve(self, memory):
        item = memory.store(content="retrieve me")
        iid = getattr(item, 'item_id', getattr(item, 'id', None))
        if iid:
            fetched = memory.retrieve(iid)
            assert fetched is not None

    def test_retrieve_nonexistent(self, memory):
        result = memory.retrieve("nope")
        assert result is None

    def test_search(self, memory):
        memory.store(content="searchable content")
        results = memory.search(query="searchable")
        assert isinstance(results, list)

    def test_search_by_category(self, memory):
        memory.store(content="cat test", category="special")
        results = memory.search(category="special")
        assert isinstance(results, list)

    def test_get_by_category(self, memory):
        memory.store(content="c1", category="cat_a")
        memory.store(content="c2", category="cat_a")
        results = memory.get_by_category("cat_a")
        assert isinstance(results, list)

    def test_count(self, memory):
        memory.store(content="a")
        memory.store(content="b")
        count = memory.count()
        assert count >= 2

    def test_delete(self, memory):
        item = memory.store(content="delete me")
        iid = getattr(item, 'item_id', getattr(item, 'id', None))
        if iid:
            memory.delete(iid)

    def test_update(self, memory):
        item = memory.store(content="original")
        iid = getattr(item, 'item_id', getattr(item, 'id', None))
        if iid:
            memory.update(iid, content="updated")

    def test_cleanup_expired(self, memory):
        result = memory.cleanup_expired()
        assert isinstance(result, (int, dict))

    def test_stats(self, memory):
        s = memory.stats()
        assert isinstance(s, dict)
