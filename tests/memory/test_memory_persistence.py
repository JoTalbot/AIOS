from core.memory.memory_persistence import MemoryPersistence


def test_memory_persistence_roundtrip():
    memory = MemoryPersistence()
    memory.save("task", {"result": "success"})

    restored = memory.load("task")

    assert restored["result"] == "success"


def test_memory_persistence_missing_key():
    memory = MemoryPersistence()

    assert memory.load("missing") is None
