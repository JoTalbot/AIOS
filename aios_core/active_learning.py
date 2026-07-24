"""Active Learning for AIOS"""

import random
from typing import Any, Dict, List

__all__ = ["ActiveLearner"]


class ActiveLearner:
    """Active learning query selection.
    __slots__ = ('labeled', 'unlabeled')

    Maintains pools of labeled and unlabeled data and supports uncertainty
    and random sampling strategies.
    """

    def __init__(self):
        """Initialize ActiveLearner."""
        self.labeled: List[Dict] = []
        self.unlabeled: List[Dict] = []

    def add_unlabeled(self, data: Dict) -> None:
        """Add *data* to the unlabeled pool."""
        self.unlabeled.append(data)

    def query(self, strategy: str = "uncertainty") -> Dict:
        """Return an item from the unlabeled pool using *strategy*.

        ``"uncertainty"`` returns the first item; ``"random"`` picks uniformly.
        """
        if not self.unlabeled:
            return {}
        if strategy == "random":
            return random.choice(self.unlabeled)
        return self.unlabeled[0]

    def label(self, data: Dict, label: Any) -> None:
        """Move *data* from the unlabeled pool to the labeled pool with *label*."""
        self.labeled.append({**data, "label": label})
        if data in self.unlabeled:
            self.unlabeled.remove(data)

    def stats(self) -> dict:
        """Return counts of labeled and unlabeled items."""
        return {"labeled": len(self.labeled), "unlabeled": len(self.unlabeled)}
