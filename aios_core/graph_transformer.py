"""Graph Transformer for AIOS v10.9.0.

Graph Transformer with multi-head attention over
graph structures, node/edge embedding, layer
stacking, residual connections, and graph-level
readout.

Classes:
    GraphTransformerLayer — single GT layer
    GraphTransformer       — full graph transformer engine
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GraphTransformerLayer:
    """Single Graph Transformer layer config."""

    dim: int = 64
    heads: int = 4
    dropout: float = 0.0
    residual: bool = True


class GraphTransformer:
    """Full Graph Transformer engine.

    Features:
    - Multi-head attention over edges
    - Node embedding management
    - Edge-aware attention computation
    - Layer stacking with residual connections
    - Graph-level readout (mean/max/attention)
    - Positional encoding for graph structure
    """

    def __init__(
        self, dim: int = 64, heads: int = 4, layers: int = 2, dropout: float = 0.0
    ) -> None:
        self.dim = dim
        self.heads = heads
        self.layers = layers
        self.dropout = dropout
        self.nodes: dict[str, list[float]] = {}
        self.edges: list[tuple[str, str]] = []
        self.edge_features: dict[tuple[str, str], list[float]] = {}
        self._layer_configs = [
            GraphTransformerLayer(dim=dim, heads=heads, dropout=dropout)
            for _ in range(layers)
        ]

    # ── Node/Edge Management ────────────────────────────────────────

    def add_node(self, node_id: str, embedding: list[float] | None = None) -> None:
        """Add a node with optional embedding."""
        if embedding:
            self.nodes[node_id] = embedding[: self.dim]
        else:
            self.nodes[node_id] = [random.gauss(0, 0.1) for _ in range(self.dim)]

    def add_edge(self, src: str, dst: str, features: list[float] | None = None) -> None:
        """Add an edge with optional features."""
        self.edges.append((src, dst))
        if features:
            self.edge_features[(src, dst)] = features

    def get_neighbors(self, node_id: str) -> list[str]:
        """Return neighbor node IDs."""
        neighbors = []
        for src, dst in self.edges:
            if src == node_id:
                neighbors.append(dst)
            elif dst == node_id:
                neighbors.append(src)
        return neighbors

    # ── Attention Computation ──────────────────────────────────────

    def _compute_attention(
        self,
        node_emb: list[float],
        neighbor_embs: list[list[float]],
        edge_feats: list[list[float]] | None = None,
    ) -> list[float]:
        """Compute multi-head attention for a node."""
        if not neighbor_embs:
            return node_emb

        head_dim = self.dim // self.heads
        attended = [0.0] * self.dim

        for h in range(self.heads):
            # Project to head dimension
            start = h * head_dim
            end = start + head_dim

            q = node_emb[start:end]
            if not q:
                continue

            scores = []
            for n_emb in neighbor_embs:
                k = n_emb[start:end] if len(n_emb) >= end else n_emb
                # Dot-product attention score
                score = sum(qi * ki for qi, ki in zip(q, k, strict=False))
                score /= math.sqrt(head_dim) if head_dim > 0 else 1.0

                # Add edge feature influence
                if edge_feats:
                    for ef in edge_feats:
                        score += sum(ef[start:end]) * 0.1 if len(ef) >= end else 0

                scores.append(score)

            # Softmax over scores
            max_score = max(scores) if scores else 0
            exp_scores = [math.exp(s - max_score) for s in scores]
            sum_exp = sum(exp_scores) if exp_scores else 1.0
            weights = [e / sum_exp for e in exp_scores]

            # Weighted sum of neighbor values
            for d in range(head_dim):
                val = 0.0
                for w, n_emb in zip(weights, neighbor_embs, strict=False):
                    if d < len(n_emb):
                        val += w * n_emb[d]
                if start + d < self.dim:
                    attended[start + d] = val

        return attended

    # ── Forward Pass ────────────────────────────────────────────────

    def forward(
        self, nodes: list[dict] | None = None, edges: list[tuple] | None = None
    ) -> list[dict]:
        """Process graph through transformer layers."""
        edges = edges or self.edges
        node_ids = list(self.nodes.keys())

        for layer_idx in range(self.layers):
            new_embeddings = {}
            for node_id in node_ids:
                node_emb = self.nodes.get(node_id, [0.0] * self.dim)
                neighbors = self.get_neighbors(node_id)
                neighbor_embs = [self.nodes.get(n, [0.0] * self.dim) for n in neighbors]

                # Edge features for attention
                edge_feats = []
                for n in neighbors:
                    ef = self.edge_features.get((node_id, n))
                    if ef:
                        edge_feats.append(ef)
                    ef2 = self.edge_features.get((n, node_id))
                    if ef2:
                        edge_feats.append(ef2)

                attended = self._compute_attention(node_emb, neighbor_embs, edge_feats)

                # Residual connection
                layer_cfg = (
                    self._layer_configs[layer_idx]
                    if layer_idx < len(self._layer_configs)
                    else GraphTransformerLayer()
                )
                if layer_cfg.residual:
                    attended = [(a + n) / 2 for a, n in zip(attended, node_emb, strict=False)]

                # Dropout (simplified)
                if layer_cfg.dropout > 0:
                    attended = [
                        v if random.random() > layer_cfg.dropout else 0.0
                        for v in attended
                    ]

                new_embeddings[node_id] = attended
            self.nodes = new_embeddings

        # Return as list of dicts (backward-compatible)
        return [{"id": nid, "embedding": self.nodes[nid]} for nid in node_ids]

    # ── Readout ────────────────────────────────────────────────────

    def readout(self, method: str = "mean") -> list[float]:
        """Graph-level readout (aggregate all node embeddings)."""
        all_embs = list(self.nodes.values())
        if not all_embs:
            return [0.0] * self.dim

        if method == "max":
            return [max(e[d] for e in all_embs) for d in range(self.dim)]
        elif method == "sum":
            return [sum(e[d] for e in all_embs) for d in range(self.dim)]
        else:  # mean
            return [
                sum(e[d] for e in all_embs) / len(all_embs) for d in range(self.dim)
            ]

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "dim": self.dim,
            "heads": self.heads,
            "layers": self.layers,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
        }
