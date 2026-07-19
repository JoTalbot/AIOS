"""AIOS Learning Engine Layer v2.1.1

Processes system experience and learning signals into reusable patterns.
"""


class LearningEngine:
    """Processes and stores system learning experiences."""

    def __init__(self):
        self.experiences = []

    def learn(self, experience: dict):
        """Record a learning experience.

        Expected keys: ``action``, ``outcome`` (success/failure),
        ``confidence`` (0..1), optional ``context``.
        """
        record = {
            "action": experience.get("action"),
            "outcome": experience.get("outcome", "unknown"),
            "confidence": experience.get("confidence", 0.5),
            "context": experience.get("context"),
        }
        self.experiences.append(record)
        return record

    def history(self):
        """Return learning history."""
        return self.experiences

    def extract_patterns(self) -> list:
        """Extract learned patterns from successful experiences."""
        patterns = []
        for exp in self.experiences:
            if exp.get("outcome") == "success":
                patterns.append({
                    "action": exp.get("action"),
                    "outcome": "success",
                    "confidence": exp.get("confidence", 0.5),
                })
        return patterns

    def success_rate(self) -> float:
        """Fraction of experiences that ended in success."""
        if not self.experiences:
            return 0.0
        ok = sum(1 for e in self.experiences if e.get("outcome") == "success")
        return round(ok / len(self.experiences), 3)
