"""Swarm Federated Learning & Consensus Engine for AIOS v11.28.0.

Aggregates privacy-preserving insights, model weights, and KnowledgeGraph deltas
across distributed AIOS swarm nodes.
"""

from __future__ import annotations

import time
from typing import Any


class SwarmFederatedEngine:
    """Privacy-preserving swarm federated aggregator."""

    def __init__(self) -> None:
        self.federated_rounds: list[dict[str, Any]] = []

    def aggregate_swarm_insights(
        self,
        nodes_insights: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate privacy-preserving weight deltas and insight statistics across nodes."""
        if not nodes_insights:
            return {"nodes_aggregated": 0, "status": "no_data"}

        total_weight = sum(n.get("sample_count", 1) for n in nodes_insights)
        aggregated_metrics: dict[str, float] = {}

        for node in nodes_insights:
            weight = node.get("sample_count", 1) / total_weight
            for k, v in node.get("metrics", {}).items():
                if isinstance(v, (int, float)):
                    aggregated_metrics[k] = aggregated_metrics.get(k, 0.0) + v * weight

        result = {
            "round_id": f"round_{len(self.federated_rounds) + 1}",
            "nodes_aggregated": len(nodes_insights),
            "total_samples": total_weight,
            "aggregated_metrics": {k: round(v, 4) for k, v in aggregated_metrics.items()},
            "timestamp": time.time(),
        }
        self.federated_rounds.append(result)
        return result
