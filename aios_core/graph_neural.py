"""Graph Neural Network Abstraction for AIOS"""

from typing import Dict, List


class GraphNeuralNetwork:
    """Simplified GNN for knowledge graph reasoning."""

    def __init__(self, layers: int = 2):
        self.layers = layers
        self.embeddings: Dict[str, List[float]] = {}

    def add_node(self, node_id: str, features: List[float]):
        self.embeddings[node_id] = features

    def message_passing(self, edges: List[tuple]) -> Dict[str, List[float]]:
        """Simple message passing simulation."""
        new_embeddings = self.embeddings.copy()
        for src, dst in edges:
            if src in self.embeddings and dst in self.embeddings:
                # Average features (simplified)
                avg = [(a + b) / 2 for a, b in zip(self.embeddings[src], self.embeddings[dst])]
                new_embeddings[dst] = avg
        self.embeddings = new_embeddings
        return self.embeddings

    def stats(self) -> dict:
        return {"nodes": len(self.embeddings), "layers": self.layers}
