class PersistenceEventHooks:
    """Binds EventBus lifecycle events to runtime persistence."""

    def __init__(self, event_bus, snapshot_store, agent_manager):
        self.event_bus = event_bus
        self.snapshot_store = snapshot_store
        self.agent_manager = agent_manager

    def register(self):
        self.event_bus.subscribe_all(self.handle_event)

    def handle_event(self, event):
        event_type = getattr(event, "type", None) or getattr(event, "name", None)

        if event_type in {
            "agent.state_changed",
            "agent.execution.completed",
            "agent.started",
            "agent.stopped",
            "agent.failed",
        }:
            self.snapshot_store.save_runtime_snapshot(
                self.agent_manager.snapshot()
            )
