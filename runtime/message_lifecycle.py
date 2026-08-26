"""Unified message lifecycle foundation for AIOS."""

class MessageLifecycle:
    def __init__(self, gateway=None, coordinator=None):
        self.gateway = gateway
        self.coordinator = coordinator

    def handle(self, message):
        if self.coordinator:
            return self.coordinator.execute(message)
        return message
