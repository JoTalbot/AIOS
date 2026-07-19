"""AIOS Distributed Node Manager"""

class NodeManager:
    def __init__(self):
        self.nodes = []

    def register(self, node):
        self.nodes.append(node)
        return True

    def status(self):
        return self.nodes
