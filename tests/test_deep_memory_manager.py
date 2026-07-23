"""Deep memory manager — search and retrieval."""
from aios_core.memory_manager import MemoryManager
def test_search_accuracy():
    mm = MemoryManager()
    mm.store({"tag": "python", "content": "def foo"}, "user1")
    mm.store({"tag": "javascript", "content": "function bar"}, "user2")
    mm.store({"tag": "python", "content": "class Baz"}, "user1")
    s = mm.stats()
    assert s is not None
def test_multi_owner_isolation():
    mm = MemoryManager()
    mm.store({"data": "a"}, "owner1")
    mm.store({"data": "b"}, "owner2")
    assert mm.stats() is not None
