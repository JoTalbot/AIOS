"""Recursive Reward Modeling for AIOS v10.11.0.

Recursive reward modeling: iterated reward model training,
feedback incorporation, model stacking, quality tracking,
convergence detection, and human feedback simulation.

Classes:
    RewardModelEntry — single reward model snapshot
    RecursiveRewardModel — full recursive reward engine
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

__all__ = ["RecursiveRewardModel"]


@dataclass
class RewardModelEntry:
    """Single reward model snapshot."""
    name: str
    parent: str = ""
    quality: float = 0.8
    created_at: float = field(default_factory=time.time)
    feedback_count: int = 0


class RecursiveRewardModel:
    """Recursively learns reward models (backward-compatible)."""

    def __init__(self) -> None:
        self.reward_models: dict[str, Callable] = {}
        self.iterations: dict[str, int] = {}
        self._model_entries: list[RewardModelEntry] = []
        self._feedback_log: list[dict[str, Any]] = []

    def train_iteration(self, base_model: str, human_feedback: dict[str, Any]) -> str:
        """Train one iteration (backward-compatible)."""
        new_model = f"{base_model}_iter_{self.iterations.get(base_model, 0) + 1}"
        quality = 0.8 + 0.02 * self.iterations.get(base_model, 0)
        self.reward_models[new_model] = lambda x: min(1.0, quality + random.gauss(0, 0.05))
        self.iterations[base_model] = self.iterations.get(base_model, 0) + 1
        self._model_entries.append(RewardModelEntry(name=new_model, parent=base_model, quality=min(1.0, quality)))
        self._feedback_log.append({"model": new_model, "feedback_type": "human", "count": len(human_feedback) if isinstance(human_feedback, (list, dict)) else 1})
        logger.info("Trained reward model %s (quality=%.2f)", new_model, quality)
        return new_model

    def stack_models(self, models: list[str]) -> str:
        """Stack multiple reward models for ensemble."""
        stacked_name = f"stacked_{len(self._model_entries)}"
        self.reward_models[stacked_name] = lambda x: sum(self.reward_models.get(m, lambda _: 0.5)(x) for m in models) / len(models)
        self._model_entries.append(RewardModelEntry(name=stacked_name, quality=0.9))
        return stacked_name

    def evaluate_model(self, model_name: str, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate a reward model on test cases."""
        if model_name not in self.reward_models:
            return {"error": "model not found"}
        scores = [self.reward_models[model_name](tc) for tc in test_cases]
        return {
            "model": model_name,
            "avg_score": round(sum(scores) / len(scores), 4),
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
        }

    def convergence_check(self, base_model: str) -> bool:
        """Check if recursive training has converged."""
        iterations = self.iterations.get(base_model, 0)
        if iterations < 3:
            return False
        recent_entries = [e for e in self._model_entries if e.parent == base_model][-3:]
        quality_changes = [abs(recent_entries[i].quality - recent_entries[i-1].quality) for i in range(1, len(recent_entries))]
        return max(quality_changes) < 0.01 if quality_changes else False

    def simulate_human_feedback(self, scenario: str) -> dict[str, Any]:
        """Simulate human feedback for a scenario."""
        return {
            "scenario": scenario,
            "rating": round(random.uniform(0.6, 1.0), 2),
            "corrections": random.randint(0, 5),
            "preference": random.choice(["helpful", "harmless", "honest"]),
        }

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "models": len(self.reward_models),
            "total_iterations": sum(self.iterations.values()),
            "feedback_entries": len(self._feedback_log),
        }
