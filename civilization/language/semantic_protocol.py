class SemanticProtocol:
    """Semantic communication protocol foundation."""

    def encode(self, meaning):
        return {
            "semantic": meaning
        }

    def decode(self, message):
        return message.get("semantic")
