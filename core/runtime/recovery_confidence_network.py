"""AIOS recovery confidence network layer."""

from datetime import datetime, timezone


class RecoveryConfidenceNetwork:
    """Tracks confidence signals across distributed recovery decisions."""

    def __init__(self):
        self.history = []
        self.peers = {}

    def record(self, decision, confidence=0.0, source="system"):
        item = {
            "source": source,
            "decision": decision,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.history.append(item)
        return item

    def register_peer(self, peer_id, confidence=0.0):
        self.peers[peer_id] = confidence
        return self.peers[peer_id]

    def consensus(self):
        if not self.peers:
            return {"confidence": 0, "peers": 0}
        values = list(self.peers.values())
        return {
            "confidence": sum(values) / len(values),
            "peers": len(values),
        }

    def rank(self):
        return sorted(self.history, key=lambda item: item.get("confidence", 0), reverse=True)

    def snapshot(self):
        return {
            "decisions": len(self.history),
            "peers": len(self.peers),
            "consensus": self.consensus(),
            "average_confidence": (
                sum(item.get("confidence", 0) for item in self.history) / len(self.history)
                if self.history else 0
            ),
        }
