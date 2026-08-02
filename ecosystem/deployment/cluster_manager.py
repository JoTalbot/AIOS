class ClusterManager:
    """Agent cluster management foundation."""

    def __init__(self):
        self.clusters = {}

    def create(self, name, agents):
        self.clusters[name] = agents

    def get(self, name):
        return self.clusters.get(name)
