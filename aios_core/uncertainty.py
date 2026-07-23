"""Uncertainty Quantification for AIOS"""

import statistics
from typing import Dict, List


class UncertaintyQuantifier:
    """Quantifies prediction uncertainty."""

    def __init__(self):
        self.predictions: Dict[str, list[float]] = {}

    def add_prediction(self, model_id: str, value: float) -> None:
        """Execute add prediction."""
        if model_id not in self.predictions:
            self.predictions[model_id] = []
        self.predictions[model_id].append(value)

    def epistemic_uncertainty(self, model_id: str) -> float:
        """Execute epistemic uncertainty."""
        preds = self.predictions.get(model_id, [])
        if len(preds) < 2:
            return 0.0
        return statistics.stdev(preds)

    def aleatoric_uncertainty(self, model_id: str) -> float:
        """Execute aleatoric uncertainty."""
        # Placeholder for data uncertainty
        return 0.1

    def total_uncertainty(self, model_id: str) -> float:
        """Execute total uncertainty."""
        return self.epistemic_uncertainty(model_id) + self.aleatoric_uncertainty(model_id)

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"models": len(self.predictions)}
