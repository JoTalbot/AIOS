"""Federated Analytics for AIOS"""

from typing import Dict, List


class FederatedAnalytics:
    """Privacy-preserving distributed analytics."""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}

    def register_node(self, node_id: str):
        self.nodes[node_id] = {"data_points": 0, "contributions": 0}

    def aggregate(self, local_stats: List[Dict]) -> Dict:
        if not local_stats:
            return {}
        total = sum(s.get("count", 0) for s in local_stats)
        avg = sum(s.get("mean", 0) for s in local_stats) / len(local_stats)
        return {"total": total, "average": round(avg, 4)}

    def stats(self) -> dict:
        return {"nodes": len(self.nodes)}