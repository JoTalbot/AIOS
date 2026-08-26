"""Integration coverage for runtime restart event flow."""


def test_restart_event_flow():
    events = []

    class EventBus:
        def publish(self, name, payload=None):
            events.append(name)

    from core.kernel.restart_events import RestartEventEmitter

    emitter = RestartEventEmitter(EventBus())
    emitter.started({"source": "test"})
    emitter.recovered({"source": "test"})
    emitter.completed({"source": "test"})

    assert "runtime.restart.started" in events
    assert "runtime.recovered" in events
    assert "runtime.restart.completed" in events
