"""Full tests for event bus."""

from aios_core.event_bus import EventBus


def test_event_bus_publish():
    eb = EventBus()
    results = []
    def handler(payload):
        results.append(payload)
    eb.on("test_event", handler)
    eb.emit("test_event", {"data": 42})
    assert len(results) == 1
    assert results[0]["data"] == 42
