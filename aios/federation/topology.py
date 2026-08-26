class FederationTopology:
    def __init__(self):
        self.nodes = {}
        self.links = {}

    def add_node(self, node_id, metadata=None):
        self.nodes[node_id] = metadata or {}

    def connect(self, source, target, latency=0):
        self.links[(source, target)] = {"latency": latency}

    def active_nodes(self):
        return list(self.nodes.keys())
