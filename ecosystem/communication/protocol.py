class CommunicationProtocol:
    """Agent communication protocol foundation."""

    def encode(self, data):
        return {
            "payload": data
        }

    def decode(self, message):
        return message.get("payload")
