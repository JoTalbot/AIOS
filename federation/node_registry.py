class NodeRegistry:
    """AIOS node registry foundation."""

    def register(self, node):
        return {
            "node": node,
            "registered": True
        }
