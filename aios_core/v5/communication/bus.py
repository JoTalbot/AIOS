class AgentCommunicationBus:
    """Message bus foundation for AIOS agents."""

    def __init__(self):
        self.messages = []

    def publish(self, sender, target, payload):
        message = {
            "sender": sender,
            "target": target,
            "payload": payload,
        }
        self.messages.append(message)
        return message

    def history(self):
        return self.messages
