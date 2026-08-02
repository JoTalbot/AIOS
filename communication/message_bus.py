class MessageBus:
    """AIOS message transport foundation."""

    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)

    def all(self):
        return self.messages
