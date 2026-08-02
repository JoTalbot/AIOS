class NodeRegistry:
    """AIOS node registry foundation."""

    def __init__(self):
        self.nodes = []

    def add(self, node):
        self.nodes.append(node)

    def list(self):
        return self.nodes
