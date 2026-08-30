class AgentIdentity:
    """Identity model for AIOS agents."""

    def __init__(self, agent_id: str, role: str, capabilities=None):
        self.agent_id = agent_id
        self.role = role
        self.capabilities = capabilities or []

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities
