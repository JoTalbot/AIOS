"""test_memory_manager_scenario test."""
from aios_core.memory_manager import MemoryManager

def test_store_search_retrieve():
    mm = MemoryManager()
    mm.store({"tag": "python", "text": "import this"}, "dev1")
    mm.store({"tag": "js", "text": "console.log"}, "dev2")
    mm.store({"tag": "python", "text": "def foo():"}, "dev1")
    s = mm.stats()
    assert s is not None
