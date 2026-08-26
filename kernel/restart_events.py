"""Runtime restart event definitions for AIOS."""


RUNTIME_RESTART_STARTED = "runtime.restart.started"
RUNTIME_RESTART_COMPLETED = "runtime.restart.completed"
RUNTIME_RECOVERED = "runtime.recovered"


class RestartEventEmitter:
    """Small adapter for publishing restart lifecycle events."""

    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def emit(self, event_name, payload=None):
        if self.event_bus is None:
            return None
        return self.event_bus.emit(event_name, payload or {})

    def started(self, payload=None):
        return self.emit(RUNTIME_RESTART_STARTED, payload)

    def completed(self, payload=None):
        return self.emit(RUNTIME_RESTART_COMPLETED, payload)

    def recovered(self, payload=None):
        return self.emit(RUNTIME_RECOVERED, payload)
