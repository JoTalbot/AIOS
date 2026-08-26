"""AIOS v21 reasoning graph foundation."""

from collections import defaultdict


class ReasoningGraph:
    def __init__(self):
        self.edges = defaultdict(list)

    def connect(self, source: str, target: str):
        self.edges[source].append(target)

    def neighbors(self, node: str):
        return self.edges.get(node, [])
