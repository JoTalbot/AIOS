class KnowledgeGraph:
    """AIOS knowledge graph foundation."""

    def __init__(self):
        self.nodes = []
        self.relations = []

    def add_node(self, node):
        self.nodes.append(node)

    def add_relation(self, relation):
        self.relations.append(relation)
