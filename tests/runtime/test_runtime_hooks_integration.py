"""Runtime integration tests for lifecycle hooks."""

from core.runtime.agent_hooks import AgentHooks


def test_runtime_lifecycle_events_are_emitted():
    events = []
    hooks = AgentHooks()

    hooks.register("runtime.start", lambda: events.append("start"))
    hooks.register("runtime.stop", lambda: events.append("stop"))

    hooks.emit("runtime.start")
    hooks.emit("runtime.stop")

    assert events == ["start", "stop"]


def test_hook_metadata_flow():
    received = []
    hooks = AgentHooks()

    hooks.register("runtime.event", lambda event: received.append(event))
    hooks.emit("runtime.event", {"source": "runtime", "state": "ready"})

    assert received[0]["state"] == "ready"
