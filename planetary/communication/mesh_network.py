class MeshNetwork:
    """Planetary mesh communication foundation."""

    def __init__(self):
        self.connections = {}

    def connect(self, source, target):
        self.connections.setdefault(source, []).append(target)

    def peers(self, node):
        return self.connections.get(node, [])
