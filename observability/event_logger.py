class EventLogger:
    """AIOS event logging foundation."""

    def __init__(self):
        self.events = []

    def log(self, event):
        self.events.append(event)

    def all(self):
        return self.events
