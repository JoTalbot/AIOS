from aios_core.runtime.events import EventBus


def test_event_bus_publishes_and_keeps_history():
    bus = EventBus()
    received = []
    bus.subscribe("TASK_COMPLETED", received.append)

    event = bus.publish("TASK_COMPLETED", "task-1", status="completed")

    assert received == [event]
    assert bus.history("task-1") == (event,)
    assert event.payload["status"] == "completed"


def test_wildcard_subscriber_receives_all_events():
    bus = EventBus()
    received = []
    bus.subscribe("*", received.append)

    bus.publish("TASK_STARTED", "task-2")
    bus.publish("TASK_FAILED", "task-2", reason="boom")

    assert [item.name for item in received] == ["TASK_STARTED", "TASK_FAILED"]
