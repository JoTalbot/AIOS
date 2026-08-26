import pytest

from execution.coordinator import ExecutionCoordinator
from execution.event_sink import ExecutionEventSink


@pytest.mark.asyncio
async def test_coordinator_uses_injected_sink_for_complete_lifecycle():
    events = []
    coordinator = ExecutionCoordinator(event_sink=ExecutionEventSink(events.append))

    result = await coordinator.execute({"task_id": "sink-1", "goal": "hello"})

    assert result["status"] == "completed"
    assert [event["type"] for event in events] == [
        "execution.started",
        "execution.completed",
    ]
    assert all(event["task_id"] == "sink-1" for event in events)
