class IdentityManager:
    """Federation node identity foundation."""

    def __init__(self):
        self.identities = {}

    def register(self, node_id, identity):
        self.identities[node_id] = identity

    def verify(self, node_id):
        return node_id in self.identities
