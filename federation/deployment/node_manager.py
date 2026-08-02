class NodeManager:
    """Federation node lifecycle management foundation."""

    def __init__(self):
        self.nodes = {}

    def register(self, node_id, node):
        self.nodes[node_id] = node

    def list_nodes(self):
        return list(self.nodes.keys())
