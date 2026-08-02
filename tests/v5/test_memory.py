from aios_core.v5.memory.short_term import ShortTermMemory


def test_short_memory():
    memory = ShortTermMemory()
    memory.remember("event")
    assert "event" in memory.get_all()
