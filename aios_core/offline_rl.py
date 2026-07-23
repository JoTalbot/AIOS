"""Offline Reinforcement Learning for AIOS"""

from typing import Dict, List


class OfflineRL:
    """Offline RL from fixed datasets."""

    def __init__(self):
        self.dataset: List[Dict] = []

    def add_transition(self, transition: Dict) -> None:
        """Execute add transition."""
        self.dataset.append(transition)

    def train(self, algorithm: str = "bcq") -> Dict:
        """Execute train."""
        return {
            "algorithm": algorithm,
            "dataset_size": len(self.dataset),
            "status": "trained",
        }

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"dataset_size": len(self.dataset)}
