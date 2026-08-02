class NodeManager:
    """AIOS node management foundation."""

    def register(self, node):
        return {
            "node": node,
            "registered": True
        }
