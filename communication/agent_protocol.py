class AgentMessage:
    def __init__(self, sender, receiver, message_type, payload):
        self.sender = sender
        self.receiver = receiver
        self.message_type = message_type
        self.payload = payload

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "type": self.message_type,
            "payload": self.payload,
        }


class AgentProtocol:
    def create(self, sender, receiver, message_type, payload):
        return AgentMessage(sender, receiver, message_type, payload)
