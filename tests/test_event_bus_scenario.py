"""test_event_bus_scenario test."""
from aios_core.event_bus import EventBus

def test_multi_event_types():
    eb = EventBus()
    r1, r2 = [], []
    eb.on("type_a", lambda p: r1.append(p))
    eb.on("type_b", lambda p: r2.append(p))
    eb.emit("type_a", {"v": 1})
    eb.emit("type_a", {"v": 2})
    eb.emit("type_b", {"v": 3})
    assert len(r1) == 2
    assert len(r2) == 1
