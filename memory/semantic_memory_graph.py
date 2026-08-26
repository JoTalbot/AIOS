class SemanticMemoryGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_knowledge(self, key, value):
        self.nodes[key] = value

    def connect(self, source, target, relation):
        self.edges.append({"source": source, "target": target, "relation": relation})

    def related(self, key):
        return [e for e in self.edges if e["source"] == key or e["target"] == key]
