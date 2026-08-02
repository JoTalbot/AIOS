class RuntimeMonitor:
    """Runtime metrics foundation."""

    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)

    def metrics(self):
        return {"events": len(self.events)}
