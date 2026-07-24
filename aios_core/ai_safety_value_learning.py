"""Value Learning and Preference Modeling for AIOS v10.11.0.

Value learning: preference collection, value inference,
coherence checking, preference aggregation, value
evolution, moral framework alignment, and conflict
resolution.

Classes:
    ValueLearning — full value learning engine
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["ValueLearning"]


class ValueLearning:
    """Learns and represents human values (backward-compatible)."""

    def __init__(self) -> None:
        self.values: dict[str, float] = {}
        self.preferences: list[dict[str, Any]] = []
        self._value_history: list[dict[str, float]] = []
        self._conflicts: list[dict[str, Any]] = []
        self._moral_frameworks: list[str] = ["utilitarian", "deontological", "virtue_ethics"]

    def learn_preference(self, option_a: str, option_b: str, preference: str) -> None:
        """Learn a preference (backward-compatible)."""
        self.preferences.append({"a": option_a, "b": option_b, "preference": preference})
        # Update value scores
        weight = 0.1
        if preference == option_a:
            self.values[option_a] = self.values.get(option_a, 0.5) + weight
            self.values[option_b] = self.values.get(option_b, 0.5) - weight * 0.5
        else:
            self.values[option_b] = self.values.get(option_b, 0.5) + weight
            self.values[option_a] = self.values.get(option_a, 0.5) - weight * 0.5
        self._value_history.append(dict(self.values))

    def infer_value(self, behavior: str) -> float:
        """Infer value score (backward-compatible)."""
        return round(self.values.get(behavior, 0.5), 2)

    def aggregate_preferences(self) -> dict[str, float]:
        """Aggregate all preferences into value scores."""
        for pref in self.preferences:
            chosen = pref["preference"]
            self.values[chosen] = self.values.get(chosen, 0.5) + 0.05
        return dict(self.values)

    def check_coherence(self) -> dict[str, Any]:
        """Check if learned values are internally coherent."""
        if len(self.preferences) < 3:
            return {"coherent": True, "inconsistencies": 0}
        inconsistencies = 0
        for p1 in self.preferences:
            for p2 in self.preferences:
                if p1["a"] == p2["b"] and p1["b"] == p2["a"] and p1["preference"] != p2["preference"]:
                    inconsistencies += 1
        return {
            "coherent": inconsistencies == 0,
            "inconsistencies": inconsistencies,
            "value_count": len(self.values),
        }

    def resolve_conflict(self, value_a: str, value_b: str) -> str:
        """Resolve a conflict between two values."""
        score_a = self.values.get(value_a, 0.5)
        score_b = self.values.get(value_b, 0.5)
        winner = value_a if score_a >= score_b else value_b
        self._conflicts.append({"a": value_a, "b": value_b, "winner": winner})
        return winner

    def align_to_framework(self, framework: str) -> dict[str, Any]:
        """Align values to a moral framework."""
        if framework not in self._moral_frameworks:
            return {"aligned": False, "error": "unknown framework"}
        adjustments = {
            "utilitarian": {"maximize_welfare": 0.9, "minimize_harm": 0.8},
            "deontological": {"follow_rules": 0.9, "respect_rights": 0.8},
            "virtue_ethics": {"act_virtuously": 0.9, "develop_character": 0.8},
        }
        for key, val in adjustments.get(framework, {}).items():
            self.values[key] = val
        return {"aligned": True, "framework": framework, "values_added": len(adjustments.get(framework, {}))}

    def evolve_values(self, new_context: str) -> dict[str, float]:
        """Evolve values based on new context."""
        for key in list(self.values.keys())[:5]:
            self.values[key] = min(1.0, self.values[key] + random.uniform(-0.02, 0.02))
        return dict(self.values)

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "preferences": len(self.preferences),
            "values": len(self.values),
            "conflicts_resolved": len(self._conflicts),
        }
