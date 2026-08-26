"""Integration event streaming foundation."""

class IntegrationEventStream:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)

    def all(self):
        return list(self.events)
