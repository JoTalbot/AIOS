"""AIOS v27.4 Recursive Intelligence Network."""

class RecursiveIntelligenceNetwork:
    def __init__(self):
        self.nodes = []

    def add_node(self, node):
        self.nodes.append(node)

    def topology(self):
        return list(self.nodes)
