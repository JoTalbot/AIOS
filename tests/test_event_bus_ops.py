"""Event bus operations tests."""
from aios_core.event_bus import EventBus
def test_event_emit():
    eb = EventBus()
    r = []
    eb.on("e", lambda p: r.append(p))
    eb.emit("e", {"x": 1})
    assert r[0]["x"] == 1
