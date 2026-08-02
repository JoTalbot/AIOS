class FederationManager:
    """AIOS federation management foundation."""

    def join(self, node):
        return {
            "node": node,
            "joined": True
        }
