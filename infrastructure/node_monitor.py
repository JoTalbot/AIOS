class NodeMonitor:
    """AIOS node monitoring foundation."""

    def check(self, node):
        return {
            "node": node,
            "healthy": True
        }
