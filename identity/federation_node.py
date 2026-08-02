class FederationNode:
    """AIOS federation node foundation."""

    def connect(self, node):
        return {
            "node": node,
            "connected": True
        }
