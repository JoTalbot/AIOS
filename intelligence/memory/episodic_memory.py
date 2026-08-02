class EpisodicMemory:
    """Experience memory foundation."""

    def __init__(self):
        self.events = []

    def store(self, event):
        self.events.append(event)

    def recall(self):
        return self.events
