class Protocol:
    """AIOS communication protocol foundation."""

    def encode(self, message):
        return {
            "message": message,
            "encoded": True
        }

    def decode(self, payload):
        return payload.get("message") if isinstance(payload, dict) else payload
