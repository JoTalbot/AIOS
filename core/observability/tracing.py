"""AIOS execution tracing foundation."""

class TraceCollector:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)

    def all(self):
        return list(self.events)
