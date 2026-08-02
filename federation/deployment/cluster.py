class ClusterManager:
    """Federation cluster control foundation."""

    def __init__(self):
        self.clusters = []

    def create(self, nodes):
        self.clusters.append(nodes)
        return nodes

    def list_clusters(self):
        return self.clusters
