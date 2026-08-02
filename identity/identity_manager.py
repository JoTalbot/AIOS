class IdentityManager:
    """AIOS identity management foundation."""

    def __init__(self):
        self.identities = {}

    def register(self, name, identity):
        self.identities[name] = identity

    def get(self, name):
        return self.identities.get(name)
