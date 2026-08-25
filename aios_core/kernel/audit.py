from datetime import datetime


class AuditLogger:
    """Minimal audit event storage for AIOS v20 kernel."""

    def __init__(self):
        self.events = []

    def record(self, event: dict):
        event["timestamp"] = datetime.utcnow().isoformat()
        self.events.append(event)

    def get_events(self):
        return self.events
