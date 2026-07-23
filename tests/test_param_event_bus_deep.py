"""Parametrized: event bus deep."""
import pytest
from aios_core.event_bus import EventBus

@pytest.mark.parametrize("events,handlers", [(1,1),(5,3),(10,5),(100,10)])
def test_event_handler_matrix(events, handlers):
    eb = EventBus()
    results = []
    for h in range(handlers):
        eb.on("matrix", lambda p, h=h: results.append((h, p)))
    for e in range(events):
        eb.emit("matrix", {"e": e})
    assert len(results) == events * handlers

@pytest.mark.parametrize("event_name", [
    "user.login","user.logout","task.create","task.complete",
    "alert.fire","backup.start","backup.end",
])
def test_named_events(event_name):
    eb = EventBus()
    called = []
    eb.on(event_name, lambda p: called.append(p))
    eb.emit(event_name, {"ts": 1})
    assert len(called) == 1
