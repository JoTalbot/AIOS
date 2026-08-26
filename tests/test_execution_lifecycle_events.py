import pytest

from execution.event_sink import ExecutionEventSink
from execution.lifecycle import ExecutionLifecycle


@pytest.mark.asyncio
async def test_lifecycle_emits_completed_event():
    events = []
    lifecycle = ExecutionLifecycle(lambda ctx: _value(), event_sink=ExecutionEventSink(events.append), task_id="t1")
    assert await lifecycle.run({}) == "ok"
    assert events[0]["type"] == "execution.completed"
    assert events[0]["task_id"] == "t1"


@pytest.mark.asyncio
async def test_lifecycle_emits_recovery_and_failed_events():
    events = []

    async def fail(ctx):
        raise RuntimeError("boom")

    lifecycle = ExecutionLifecycle(fail, retries=1, event_sink=ExecutionEventSink(events.append), task_id="t2")
    with pytest.raises(RuntimeError, match="boom"):
        await lifecycle.run({})
    assert [event["type"] for event in events] == [
        "execution.recovery",
        "execution.recovery",
        "execution.failed",
    ]


async def _value():
    return "ok"
