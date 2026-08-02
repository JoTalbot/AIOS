class FederationEvents:
    """Federation event bus foundation."""

    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)

    def list_events(self):
        return self.events
