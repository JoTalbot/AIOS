"""Value Learning and Preference Modeling for AIOS"""

from typing import Dict, List


class ValueLearning:
    """Learns and represents human values."""

    def __init__(self):
        self.values: Dict[str, float] = {}
        self.preferences: List[Dict] = []

    def learn_preference(self, option_a: str, option_b: str, preference: str):
        self.preferences.append({
            "a": option_a,
            "b": option_b,
            "preference": preference
        })

    def infer_value(self, behavior: str) -> float:
        return 0.8

    def stats(self) -> dict:
        return {"preferences": len(self.preferences)}