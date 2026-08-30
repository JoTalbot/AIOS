from .models import FederationNode, Federation

class FederationRuntime:
    def __init__(self, federation: Federation):
        self.federation = federation

    def register_node(self, node: FederationNode):
        self.federation.nodes.append(node)

    def discover_nodes(self):
        return self.federation.nodes
