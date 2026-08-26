"""Runtime restart orchestration for AIOS kernel stack."""

from .restart_events import RestartEventEmitter


class RestartManager:
    """Coordinates restart operations and emits lifecycle events."""

    def __init__(self, context, event_emitter=None):
        self.context = context
        self.events = event_emitter or RestartEventEmitter(
            getattr(context, "event_bus", None)
        )

    def restart(self):
        self.events.started({"source": "restart_manager"})
        self.context.stop()
        self.context.start()
        self.events.recovered({"source": "restart_manager"})
        self.events.completed({"source": "restart_manager"})
        return self.context
