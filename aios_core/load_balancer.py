"""AIOS Load Balancer Layer v2.1.1"""

class LoadBalancer:
    def __init__(self):
        self.nodes = []

    def add_node(self, node):
        self.nodes.append(node)

    def distribute(self, task):
        return task
