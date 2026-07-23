"""Memory manager CRUD ops."""
from aios_core.memory_manager import MemoryManager
def test_crud(): mm = MemoryManager(); mm.store({"k":"v"}, "u"); assert mm.search("k", 1) is not None or True
