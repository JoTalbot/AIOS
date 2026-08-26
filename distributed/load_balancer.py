class LoadBalancer:
    def __init__(self):
        self.nodes = []

    def register(self, node):
        self.nodes.append(node)

    def select(self):
        if not self.nodes:
            return None
        return min(self.nodes, key=lambda n: n.get("load", 0))
