"""AIOS Network Coordinator"""

class NetworkCoordinator:
    def __init__(self):
        self.connections = {}

    def connect(self, node, endpoint):
        self.connections[node] = endpoint
        return True

    def get_connections(self):
        return self.connections
