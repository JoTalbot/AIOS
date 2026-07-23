"""Parametrized event bus types."""
import pytest
from aios_core.event_bus import EventBus

@pytest.mark.parametrize("event_type", [
    "user_created", "task_completed", "alert_fired", "deploy_started",
    "backup_created", "approval_needed",
])
def test_multi_event_types(event_type):
    eb = EventBus()
    results = []
    eb.on(event_type, lambda p: results.append((event_type, p)))
    eb.emit(event_type, {"ts": 1})
    assert len(results) == 1
    assert results[0][0] == event_type
