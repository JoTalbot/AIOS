class FederationProtocol:
    """Federation communication protocol foundation."""

    def encode(self, message):
        return {
            "payload": message
        }

    def decode(self, packet):
        return packet.get("payload")
