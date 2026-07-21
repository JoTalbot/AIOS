"""Active Learning for AIOS"""

from typing import List, Dict, Any
import random


class ActiveLearner:
    """Active learning query selection."""

    def __init__(self):
        self.labeled: List[Dict] = []
        self.unlabeled: List[Dict] = []

    def add_unlabeled(self, data: Dict):
        self.unlabeled.append(data)

    def query(self, strategy: str = "uncertainty") -> Dict:
        if not self.unlabeled:
            return {}
        if strategy == "random":
            return random.choice(self.unlabeled)
        # Uncertainty sampling (simplified)
        return self.unlabeled[0]

    def label(self, data: Dict, label: Any):
        self.labeled.append({**data, "label": label})
        if data in self.unlabeled:
            self.unlabeled.remove(data)

    def stats(self) -> dict:
        return {"labeled": len(self.labeled), "unlabeled": len(self.unlabeled)}