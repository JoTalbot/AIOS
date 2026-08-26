"""Runtime restart orchestration for AIOS kernel stack."""

from .restart_events import RestartEventEmitter


class RestartManager:
    """Coordinates restart operations and emits lifecycle events."""

    def __init__(self, context, event_emitter=None):
        self.context = context
        self.events = event_emitter or RestartEventEmitter()

    def restart(self):
        self.events.emit("runtime.restart.started")
        self.context.stop()
        self.context.start()
        self.events.emit("runtime.restart.completed")
        self.events.emit("runtime.recovered")
        return self.context
