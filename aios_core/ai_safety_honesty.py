"""AI Honesty and Truthfulness Framework"""

from typing import Dict, List

__all__ = ["HonestyFramework"]


class HonestyFramework:
    """Ensures AI systems are honest and truthful."""

    def __init__(self):
        self.honesty_violations: List[Dict] = []

    def check_honesty(self, statement: str, ground_truth: str = None) -> Dict:
        if ground_truth and statement != ground_truth:
            violation = {
                "statement": statement,
                "ground_truth": ground_truth,
                "type": "falsehood",
            }
            self.honesty_violations.append(violation)
            return {"honest": False, "violation": violation}
        return {"honest": True}

    def stats(self) -> dict:
        return {"violations": len(self.honesty_violations)}
