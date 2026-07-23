"""Edge: memory manager large store."""
from aios_core.memory_manager import MemoryManager
def test_large_store():
    mm = MemoryManager()
    for i in range(1000):
        mm.store({"idx": i, "data": f"value_{i}" * 10}, f"owner_{i % 10}")
    assert mm.stats() is not None
