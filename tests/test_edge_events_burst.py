"""Edge: event bus burst."""
from aios_core.event_bus import EventBus
def test_burst():
    eb = EventBus()
    count = [0]
    eb.on("ping", lambda p: count.__setitem__(0, count[0] + 1))
    for _ in range(500):
        eb.emit("ping", {})
    assert count[0] == 500
