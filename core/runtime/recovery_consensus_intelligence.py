"""AIOS multi-agent recovery consensus intelligence layer."""

from datetime import datetime, timezone


class RecoveryConsensusIntelligence:
    """Aggregates recovery votes and produces ranked consensus decisions."""

    def __init__(self):
        self.votes = []
        self.decisions = []

    def vote(self, agent, decision, confidence=0.0):
        item = {
            "agent": agent,
            "decision": decision,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.votes.append(item)
        return item

    def consensus(self):
        if not self.votes:
            return {"decision": None, "confidence": 0.0, "votes": 0}

        grouped = {}
        for vote in self.votes:
            key = str(vote["decision"])
            grouped.setdefault(key, []).append(vote)

        winner = max(
            grouped.values(),
            key=lambda items: sum(item["confidence"] for item in items) / len(items),
        )

        result = {
            "decision": winner[0]["decision"],
            "confidence": sum(item["confidence"] for item in winner) / len(winner),
            "votes": len(winner),
        }
        self.decisions.append(result)
        return result

    def snapshot(self):
        return {
            "votes": len(self.votes),
            "decisions": len(self.decisions),
            "latest": self.decisions[-1] if self.decisions else None,
        }
