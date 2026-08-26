"""Persistence hooks for AIOS runtime lifecycle events."""


class PersistenceEventHooks:
    """Stores lifecycle events through a persistence backend adapter."""

    def __init__(self, persistence=None):
        self.persistence = persistence

    def record(self, event_name, payload=None):
        event = {
            "name": event_name,
            "payload": payload or {},
        }
        if self.persistence is None:
            return event
        if hasattr(self.persistence, "append"):
            self.persistence.append(event)
        elif hasattr(self.persistence, "save"):
            self.persistence.save(event)
        return event

    def on_event(self, event_name, payload=None):
        return self.record(event_name, payload)
