from aios_core.memory_manager import MemoryManager
def test_store_retrieve():
    mm = MemoryManager()
    mm.store({'k': 'v'}, 'owner')
    assert mm.stats() is not None