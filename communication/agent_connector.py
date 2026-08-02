class AgentConnector:
    """AIOS agent connection foundation."""

    def connect(self, agent):
        return {
            "agent": agent,
            "connected": True
        }
