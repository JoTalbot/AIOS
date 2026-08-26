from dataclasses import dataclass


@dataclass
class AgentNode:
    name: str
    capabilities: list
    active: bool = True


class AgentDiscovery:

    def __init__(self):
        self.nodes = {}

    def register(self, node):
        self.nodes[node.name] = node

    def find(self, capability):
        return [
            node for node in self.nodes.values()
            if capability in node.capabilities and node.active
        ]
