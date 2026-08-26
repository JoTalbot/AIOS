"""Runtime persistence adapter for AIOS lifecycle state."""


class PersistenceRuntimeAdapter:
    """Connects runtime lifecycle events with persistence hooks."""

    def __init__(self, bridge=None):
        self.bridge = bridge

    def attach(self, emitter):
        if emitter is None:
            return False
        if self.bridge is not None and hasattr(self.bridge, "attach"):
            self.bridge.attach(emitter)
        return True

    def history(self):
        if self.bridge is None:
            return []
        if hasattr(self.bridge, "history"):
            return self.bridge.history()
        return []

    def last_recovery(self):
        events = self.history()
        for event in reversed(events):
            if event.get("type") == "runtime.recovered":
                return event
        return None
