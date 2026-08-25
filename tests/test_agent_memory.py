from aios_core.runtime.events import EventBus
from aios_core.runtime.memory import TaskMemory


def test_task_memory_receives_and_reconstructs_context():
    bus = EventBus()
    memory = TaskMemory()
    memory.attach(bus)

    bus.publish("AGENT_STARTED", "task-1", status="running")
    bus.publish("AGENT_COMPLETED", "task-1", status="completed", verdict="APPROVED")

    entries = memory.entries("task-1")
    assert len(entries) == 2
    assert entries[-1].payload["verdict"] == "APPROVED"
    assert memory.context("task-1")[0]["event"] == "AGENT_STARTED"
