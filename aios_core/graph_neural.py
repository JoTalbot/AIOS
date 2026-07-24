"""Graph Neural Network Abstraction for AIOS v10.8.0.

Simplified GNN with node embeddings, message passing,
graph convolution, node classification, edge feature
support, graph pooling, and readout functions.

Classes:
    GNNLayer      — single GNN message-passing layer
    GraphNeuralNetwork — full GNN engine
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GNNLayer:
    """Single GNN message-passing layer configuration."""

    name: str
    aggregation: str = "mean"  # mean, sum, max
    activation: str = "relu"  # relu, sigmoid, tanh, none
    dropout: float = 0.0
    normalize: bool = True


class GraphNeuralNetwork:
    """Full GNN engine.

    Features:
    - Node/edge registration with features
    - Message passing with multiple aggregation modes
    - Multi-layer graph convolution
    - Node classification (predict labels)
    - Edge feature integration
    - Graph pooling (mean/max/attention)
    - Readout functions for graph-level predictions
    """

    def __init__(self, layers: int = 2, hidden_dim: int = 16) -> None:
        self.layers = layers
        self.hidden_dim = hidden_dim
        self.embeddings: dict[str, list[float]] = {}
        self.edge_features: dict[tuple[str, str], list[float]] = {}
        self.edges: list[tuple[str, str]] = []
        self.node_labels: dict[str, str] = {}
        self._gnn_layers: list[GNNLayer] = []
        self._layer_counter = 0

        # Initialize default layers
        for i in range(layers):
            self._gnn_layers.append(
                GNNLayer(
                    name=f"layer_{i}",
                    aggregation="mean",
                    activation="relu" if i < layers - 1 else "none",
                )
            )

    # ── Node Management ──────────────────────────────────────────────

    def add_node(self, node_id: str, features: list[float], label: str = "") -> None:
        """Add a node with features and optional label."""
        self.embeddings[node_id] = features
        if label:
            self.node_labels[node_id] = label

    def remove_node(self, node_id: str) -> None:
        """Remove a node and its edges."""
        self.embeddings.pop(node_id, None)
        self.node_labels.pop(node_id, None)
        self.edges = [(s, d) for s, d in self.edges if s != node_id and d != node_id]

    def get_node(self, node_id: str) -> list[float] | None:
        """Return node embedding."""
        return self.embeddings.get(node_id)

    # ── Edge Management ──────────────────────────────────────────────

    def add_edge(self, src: str, dst: str, features: list[float] | None = None) -> None:
        """Add an edge with optional features."""
        self.edges.append((src, dst))
        if features:
            self.edge_features[(src, dst)] = features

    def add_edges(
        self,
        edge_list: list[tuple[str, str]],
        features: list[list[float]] | None = None,
    ) -> None:
        """Add multiple edges."""
        for i, (src, dst) in enumerate(edge_list):
            self.edges.append((src, dst))
            if features and i < len(features):
                self.edge_features[(src, dst)] = features[i]

    def get_neighbors(self, node_id: str) -> list[str]:
        """Return neighbors of a node."""
        neighbors = []
        for src, dst in self.edges:
            if src == node_id:
                neighbors.append(dst)
            elif dst == node_id:
                neighbors.append(src)
        return neighbors

    # ── Message Passing ──────────────────────────────────────────────

    def _aggregate(
        self, messages: list[list[float]], method: str = "mean"
    ) -> list[float]:
        """Aggregate messages from neighbors."""
        if not messages:
            return [0.0] * self.hidden_dim
        dim = len(messages[0])
        if method == "sum":
            return [sum(m[d] for m in messages) for d in range(dim)]
        elif method == "max":
            return [max(m[d] for m in messages) for d in range(dim)]
        else:  # mean
            n = len(messages)
            return [sum(m[d] for m in messages) / n for d in range(dim)]

    def _activate(self, values: list[float], activation: str = "relu") -> list[float]:
        """Apply activation function."""
        if activation == "relu":
            return [max(0, v) for v in values]
        elif activation == "sigmoid":
            return [1 / (1 + math.exp(-v)) for v in values]
        elif activation == "tanh":
            return [math.tanh(v) for v in values]
        return values  # none

    def _normalize(self, values: list[float]) -> list[float]:
        """L2 normalize a vector."""
        norm = math.sqrt(sum(v * v for v in values))
        if norm == 0:
            return values
        return [v / norm for v in values]

    def message_passing(
        self, edges: list[tuple[str, str]] | None = None, num_layers: int | None = None
    ) -> dict[str, list[float]]:
        """Run message passing across layers."""
        edge_set = edges if edges is not None else self.edges
        n_layers = num_layers or len(self._gnn_layers)

        for layer_idx in range(n_layers):
            layer = (
                self._gnn_layers[layer_idx]
                if layer_idx < len(self._gnn_layers)
                else GNNLayer(name=f"l{layer_idx}")
            )
            new_embeddings = {}

            for node_id, current_emb in self.embeddings.items():
                # Collect messages from neighbors
                neighbor_messages = []
                for src, dst in edge_set:
                    if dst == node_id and src in self.embeddings:
                        # Message: neighbor embedding + edge features if available
                        msg = self.embeddings[src]
                        edge_feat = self.edge_features.get((src, dst))
                        if edge_feat:
                            msg = msg + edge_feat
                        neighbor_messages.append(msg)
                    elif src == node_id and dst in self.embeddings:
                        msg = self.embeddings[dst]
                        edge_feat = self.edge_features.get((src, node_id))
                        if edge_feat:
                            msg = msg + edge_feat
                        neighbor_messages.append(msg)

                # Aggregate and combine
                aggregated = self._aggregate(neighbor_messages, layer.aggregation)
                combined = [(a + b) / 2 for a, b in zip(current_emb, aggregated)]

                # Activate
                activated = self._activate(combined, layer.activation)

                # Normalize
                if layer.normalize:
                    activated = self._normalize(activated)

                # Dropout (simplified: zero out random elements)
                if layer.dropout > 0:
                    activated = [
                        v if random.random() > layer.dropout else 0.0 for v in activated
                    ]

                new_embeddings[node_id] = activated

            self.embeddings = new_embeddings

        return self.embeddings

    # ── Node Classification ──────────────────────────────────────────

    def classify_node(self, node_id: str) -> str:
        """Predict node label from embedding."""
        emb = self.embeddings.get(node_id)
        if emb is None:
            return "unknown"

        # Simple heuristic: classify by embedding magnitude pattern
        if len(self.node_labels) > 0:
            # Find nearest labeled node
            best_label = "unknown"
            best_sim = -1.0
            for labeled_id, label in self.node_labels.items():
                labeled_emb = self.embeddings.get(labeled_id)
                if labeled_emb:
                    sim = self._cosine_similarity(emb, labeled_emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_label = label
            return best_label

        return "class_0"

    def classify_all(self) -> dict[str, str]:
        """Classify all unlabeled nodes."""
        results = {}
        for node_id in self.embeddings:
            if node_id not in self.node_labels:
                results[node_id] = self.classify_node(node_id)
        return results

    # ── Graph Pooling ────────────────────────────────────────────────

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na > 0 and nb > 0 else 0.0

    def graph_pool(self, method: str = "mean") -> list[float]:
        """Graph-level pooling (readout function)."""
        if not self.embeddings:
            return [0.0] * self.hidden_dim

        all_embs = list(self.embeddings.values())
        if not all_embs:
            return [0.0] * self.hidden_dim

        dim = len(all_embs[0])

        if method == "max":
            return [max(e[d] for e in all_embs) for d in range(dim)]
        elif method == "sum":
            return [sum(e[d] for e in all_embs) for d in range(dim)]
        else:  # mean
            n = len(all_embs)
            return [sum(e[d] for e in all_embs) / n for d in range(dim)]

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        labeled = len(self.node_labels)
        unlabeled = len(self.embeddings) - labeled
        return {
            "nodes": len(self.embeddings),
            "edges": len(self.edges),
            "layers": len(self._gnn_layers),
            "labeled_nodes": labeled,
            "unlabeled_nodes": unlabeled,
            "edge_features": len(self.edge_features),
        }
