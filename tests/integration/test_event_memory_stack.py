from core.events.bus import EventBus
from core.memory.backend import InMemoryBackend


def test_event_memory_stack():
    bus = EventBus()
    memory = InMemoryBackend()
    memory.save("state", "ok")
    assert memory.load("state") == "ok"
