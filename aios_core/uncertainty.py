"""Uncertainty Quantification for AIOS v10.9.0.

Prediction uncertainty quantification with epistemic,
aleatoric, and total uncertainty decomposition, ensemble
disagreement, confidence intervals, and calibration.

Classes:
    UncertaintyEstimate — uncertainty estimate for a prediction
    UncertaintyQuantifier — full uncertainty engine
"""

from __future__ import annotations

import logging
import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UncertaintyEstimate:
    """Uncertainty estimate for a prediction."""
    model_id: str
    prediction: float = 0.0
    epistemic: float = 0.0
    aleatoric: float = 0.0
    total: float = 0.0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


class UncertaintyQuantifier:
    """Full uncertainty quantification engine.

    Features:
    - Epistemic uncertainty (model uncertainty from ensemble variance)
    - Aleatoric uncertainty (data noise estimation)
    - Total uncertainty decomposition
    - Ensemble disagreement
    - Confidence interval estimation
    - Calibration tracking
    """

    def __init__(self) -> None:
        self.predictions: dict[str, list[float]] = {}
        self._estimates: list[UncertaintyEstimate] = []
        self._calibration_log: list[dict[str, Any]] = []

    def add_prediction(self, model_id: str, value: float) -> None:
        """Add a prediction (backward-compatible)."""
        if model_id not in self.predictions:
            self.predictions[model_id] = []
        self.predictions[model_id].append(value)

    def add_predictions(self, model_id: str, values: list[float]) -> None:
        """Add multiple predictions."""
        for v in values:
            self.add_prediction(model_id, v)

    def epistemic_uncertainty(self, model_id: str) -> float:
        """Compute epistemic uncertainty (backward-compatible)."""
        preds = self.predictions.get(model_id, [])
        if len(preds) < 2:
            return 0.0
        return statistics.stdev(preds)

    def aleatoric_uncertainty(self, model_id: str) -> float:
        """Compute aleatoric uncertainty (backward-compatible)."""
        # Estimate from noise in predictions (IQR-based)
        preds = self.predictions.get(model_id, [])
        if len(preds) < 4:
            return 0.1  # default noise level
        sorted_preds = sorted(preds)
        q1 = sorted_preds[len(sorted_preds) // 4]
        q3 = sorted_preds[3 * len(sorted_preds) // 4]
        return round((q3 - q1) / 2, 4)

    def total_uncertainty(self, model_id: str) -> float:
        """Compute total uncertainty (backward-compatible)."""
        return self.epistemic_uncertainty(model_id) + self.aleatoric_uncertainty(model_id)

    def ensemble_disagreement(self) -> float:
        """Measure disagreement across all models."""
        if len(self.predictions) < 2:
            return 0.0

        # Compute variance of mean predictions across models
        means = [statistics.mean(preds) for preds in self.predictions.values() if preds]
        if len(means) < 2:
            return 0.0
        return statistics.stdev(means)

    def confidence_interval(self, model_id: str, level: float = 0.95) -> tuple[float, float]:
        """Compute confidence interval for predictions."""
        preds = self.predictions.get(model_id, [])
        if len(preds) < 2:
            return (0.0, 0.0)

        mean = statistics.mean(preds)
        std = statistics.stdev(preds)
        n = len(preds)
        # 95% CI: mean ± 1.96 * std / sqrt(n)
        z = 1.96 if level == 0.95 else 2.576 if level == 0.99 else 1.0
        margin = z * std / math.sqrt(n)
        return (round(mean - margin, 4), round(mean + margin, 4))

    def estimate(self, model_id: str, prediction: float = 0.0) -> UncertaintyEstimate:
        """Compute full uncertainty estimate."""
        ep = self.epistemic_uncertainty(model_id)
        al = self.aleatoric_uncertainty(model_id)
        tot = ep + al
        confidence = max(0, min(1, 1.0 - tot * 0.5))

        est = UncertaintyEstimate(
            model_id=model_id, prediction=prediction,
            epistemic=round(ep, 4), aleatoric=round(al, 4),
            total=round(tot, 4), confidence=round(confidence, 4),
        )
        self._estimates.append(est)
        return est

    def calibrate(self, true_values: list[float], model_id: str) -> float:
        """Calibrate uncertainty estimates against true values."""
        preds = self.predictions.get(model_id, [])
        if not preds or not true_values:
            return 0.0

        # Compute mean absolute error
        min_len = min(len(preds), len(true_values))
        mae = sum(abs(preds[i] - true_values[i]) for i in range(min_len)) / min_len

        # Calibration error: ratio of predicted std to MAE
        std = statistics.stdev(preds) if len(preds) >= 2 else mae
        calibration = std / mae if mae > 0 else 1.0

        self._calibration_log.append({
            "model_id": model_id, "mae": round(mae, 4),
            "calibration_ratio": round(calibration, 4),
        })
        return round(calibration, 4)

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        return {
            "models": len(self.predictions),
            "total_predictions": sum(len(p) for p in self.predictions.values()),
            "estimates": len(self._estimates),
            "ensemble_disagreement": round(self.ensemble_disagreement(), 4),
        }
