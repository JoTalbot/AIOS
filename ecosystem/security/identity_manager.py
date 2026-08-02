class IdentityManager:
    """Agent identity management foundation."""

    def __init__(self):
        self.identities = {}

    def register(self, agent, identity):
        self.identities[agent] = identity

    def get(self, agent):
        return self.identities.get(agent)
