import pytest

from execution.coordinator import ExecutionCoordinator
from execution.event_sink import ExecutionEventSink


@pytest.mark.asyncio
async def test_coordinator_emits_canonical_success_event():
    events = []
    coordinator = ExecutionCoordinator(event_sink=ExecutionEventSink(events.append))
    result = await coordinator.execute({"task_id": "task-1", "goal": "test"})
    assert result["status"] == "completed"
    assert events[-1]["type"] == "execution.completed"
    assert events[-1]["task_id"] == "task-1"


@pytest.mark.asyncio
async def test_coordinator_emits_recovery_and_failure_events():
    events = []

    async def fail(**kwargs):
        raise RuntimeError("boom")

    coordinator = ExecutionCoordinator(
        agent_runner=fail,
        event_sink=ExecutionEventSink(events.append),
    )
    with pytest.raises(RuntimeError, match="boom"):
        await coordinator.execute({"task_id": "task-2", "goal": "test"})

    assert [event["type"] for event in events] == [
        "execution.recovery",
        "execution.failed",
    ]
