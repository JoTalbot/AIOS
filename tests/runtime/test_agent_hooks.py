from core.runtime.agent_hooks import AgentHooks


def test_hook_register_emit_and_unregister():
    hooks = AgentHooks()
    events = []

    def callback(value):
        events.append(value)

    hooks.register("start", callback)
    hooks.emit("start", "agent")

    assert events == ["agent"]

    hooks.unregister("start", callback)
    hooks.emit("start", "ignored")

    assert events == ["agent"]


def test_hook_metadata_event():
    hooks = AgentHooks()
    received = []

    hooks.register("run", lambda event: received.append(event.metadata))
    hooks.emit("run", metadata={"agent_id": "test"})

    assert received[0]["agent_id"] == "test"
