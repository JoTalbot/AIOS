"""AIOS recovery confidence network layer."""

from datetime import datetime, timezone


class RecoveryConfidenceNetwork:
    """Tracks confidence signals across distributed recovery decisions."""

    def __init__(self):
        self.history = []
        self.peers = {}
        self.votes = []

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

    def vote(self, peer_id, decision, confidence=0.0):
        vote = {
            "peer": peer_id,
            "decision": decision,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.votes.append(vote)
        self.register_peer(peer_id, confidence)
        return vote

    def consensus(self):
        if not self.peers:
            return {"confidence": 0, "peers": 0, "decision": None}
        ranking = self.rank_votes()
        decision = ranking[0]["decision"] if ranking else None
        values = list(self.peers.values())
        return {
            "confidence": sum(values) / len(values),
            "peers": len(values),
            "decision": decision,
        }

    def rank_votes(self):
        grouped = {}
        for vote in self.votes:
            key = str(vote.get("decision"))
            grouped.setdefault(key, {"decision": vote.get("decision"), "confidence": 0, "votes": 0})
            grouped[key]["confidence"] += vote.get("confidence", 0)
            grouped[key]["votes"] += 1
        return sorted(grouped.values(), key=lambda item: item["confidence"], reverse=True)

    def rank(self):
        return sorted(self.history, key=lambda item: item.get("confidence", 0), reverse=True)

    def snapshot(self):
        return {
            "decisions": len(self.history),
            "peers": len(self.peers),
            "votes": len(self.votes),
            "consensus": self.consensus(),
            "average_confidence": (
                sum(item.get("confidence", 0) for item in self.history) / len(self.history)
                if self.history else 0
            ),
        }
