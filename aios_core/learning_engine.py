"""AIOS Learning Engine Layer v2.1.1

Processes system experience and learning signals.
"""


class LearningEngine:
    """Processes and stores system learning experiences."""

    def __init__(self):
        self.experiences = []

    def learn(self, experience: dict):
        """Record a learning experience."""
        self.experiences.append(experience)
        return experience

    def history(self):
        """Return learning history."""
        return self.experiences

    def extract_patterns(self) -> list:
        """Extract learned patterns from experiences."""
        patterns = []
        for exp in self.experiences:
            if exp.get("success"):
                patterns.append({
                    "action": exp.get("action"),
                    "outcome": "success",
                    "confidence": exp.get("confidence", 0.5)
                })
        return patterns
