"""AIOS recovery confidence network layer."""

from datetime import datetime, timezone


class RecoveryConfidenceNetwork:
    """Tracks confidence signals across distributed recovery decisions."""

    def __init__(self):
        self.history = []

    def record(self, decision, confidence=0.0, source="system"):
        item = {
            "source": source,
            "decision": decision,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.history.append(item)
        return item

    def rank(self):
        return sorted(self.history, key=lambda item: item.get("confidence", 0), reverse=True)

    def snapshot(self):
        return {
            "decisions": len(self.history),
            "average_confidence": (
                sum(item.get("confidence", 0) for item in self.history) / len(self.history)
                if self.history else 0
            ),
        }
