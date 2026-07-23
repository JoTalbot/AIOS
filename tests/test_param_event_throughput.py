"""Parametrized event bus throughput."""
import pytest
from aios_core.event_bus import EventBus

@pytest.mark.parametrize("n_events", [1, 10, 100, 1000])
def test_event_throughput(n_events):
    eb = EventBus()
    results = []
    eb.on("bench", lambda p: results.append(p))
    for i in range(n_events):
        eb.emit("bench", {"idx": i})
    assert len(results) == n_events

@pytest.mark.parametrize("n_handlers", [1, 3, 10])
def test_multi_handler(n_handlers):
    eb = EventBus()
    counts = [0] * n_handlers
    for i in range(n_handlers):
        eb.on("multi", lambda p, idx=i: counts.__setitem__(idx, counts[idx] + 1))
    eb.emit("multi", {})
    assert sum(counts) >= n_handlers
