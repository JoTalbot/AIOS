"""Memory manager full tests."""
from aios_core.memory_manager import MemoryManager
def test_memory_search(): 
    mm = MemoryManager()
    assert mm.search("test", 3) == []
def test_memory_store():
    mm = MemoryManager()
    mm.store({"k": "v"}, "u")
    assert mm.stats() is not None
