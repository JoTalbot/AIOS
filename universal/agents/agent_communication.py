class AgentCommunication:
    """Universal agent communication foundation."""

    def send(self, source, target, message):
        return {
            "source": source,
            "target": target,
            "message": message
        }
