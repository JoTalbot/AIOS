class KnowledgeGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, node_id, data):
        self.nodes[node_id] = data

    def connect(self, source, target, relation):
        self.edges.append({
            "source": source,
            "target": target,
            "relation": relation
        })

    def get(self, node_id):
        return self.nodes.get(node_id)
