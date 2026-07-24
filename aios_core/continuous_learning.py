"""Continuous Learning Pipeline for AIOS v10.9.0.

Online/continuous learning with experience ingestion,
model updating, prediction, drift detection, and
performance tracking.

Classes:
    LearningState  — model learning state
    ContinuousLearning — full continuous learning engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LearningState:
    """Model learning state."""

    version: int = 0
    last_update: float = 0.0
    drift_detected: bool = False


class ContinuousLearning:
    """Full continuous learning engine.

    Features:
    - Experience ingestion
    - Model update tracking
    - Prediction with drift awareness
    - Drift detection
    - Performance monitoring
    """

    def __init__(self, drift_threshold: float = 0.3) -> None:
        self.knowledge_base: list[dict[str, Any]] = []
        self.performance_history: list[float] = []
        self._state = LearningState()
        self.drift_threshold = drift_threshold
        self._drift_log: list[dict[str, Any]] = []

    def ingest_experience(self, experience: dict[str, Any]) -> None:
        """Ingest experience (backward-compatible)."""
        self.knowledge_base.append(experience)
        self._state.version += 1
        self._state.last_update = time.time()

    def update_model(self, feedback: float) -> None:
        """Update model with feedback (backward-compatible)."""
        self.performance_history.append(feedback)

        # Detect drift
        if len(self.performance_history) >= 10:
            recent = self.performance_history[-5:]
            older = self.performance_history[-10:-5]
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            if abs(recent_avg - older_avg) > self.drift_threshold:
                self._state.drift_detected = True
                self._drift_log.append(
                    {
                        "recent_avg": round(recent_avg, 4),
                        "older_avg": round(older_avg, 4),
                        "drift": round(abs(recent_avg - older_avg), 4),
                        "timestamp": time.time(),
                    }
                )
            else:
                self._state.drift_detected = False

    def predict(self, input_data: dict[str, Any]) -> float:
        """Predict based on performance (backward-compatible)."""
        if not self.performance_history:
            return 0.5
        recent = self.performance_history[-10:]
        avg = sum(recent) / len(recent)
        # Adjust for drift
        if self._state.drift_detected:
            avg *= 0.8  # lower confidence during drift
        return round(avg, 4)

    def detect_drift(self) -> dict[str, Any]:
        """Explicit drift detection."""
        if len(self.performance_history) < 10:
            return {"drift": False, "confidence": 0.0}

        recent_avg = sum(self.performance_history[-5:]) / 5
        older_avg = sum(self.performance_history[-10:-5]) / 5
        drift = abs(recent_avg - older_avg)

        return {
            "drift": drift > self.drift_threshold,
            "drift_magnitude": round(drift, 4),
            "threshold": self.drift_threshold,
        }

    def learning_stats(self) -> dict[str, Any]:
        """Return learning state."""
        return {
            "version": self._state.version,
            "drift_detected": self._state.drift_detected,
            "drift_events": len(self._drift_log),
        }

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        avg_perf = (
            (sum(self.performance_history) / len(self.performance_history))
            if self.performance_history
            else 0
        )
        return {
            "experiences": len(self.knowledge_base),
            "avg_performance": round(avg_perf, 4),
            "drift_detected": self._state.drift_detected,
            "model_version": self._state.version,
        }
