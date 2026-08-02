class GlobalMessageBus:
    """Planetary global message exchange foundation."""

    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)

    def consume(self):
        return self.messages
