class CommunicationBus:
    """AIOS agent communication foundation."""

    def send(self, message):
        return {
            "message": message,
            "sent": True
        }
