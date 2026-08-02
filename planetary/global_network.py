class GlobalNetwork:
    """Planetary network foundation."""

    def __init__(self):
        self.nodes = []

    def add_node(self, node):
        self.nodes.append(node)

    def topology(self):
        return self.nodes
