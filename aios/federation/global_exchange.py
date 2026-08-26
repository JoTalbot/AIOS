"""Global exchange bridge for planetary federation."""

class GlobalExchange:
    def __init__(self):
        self.channels = {}

    def publish(self, topic: str, payload):
        self.channels.setdefault(topic, []).append(payload)

    def exchange(self, topic: str):
        return self.channels.get(topic, [])
