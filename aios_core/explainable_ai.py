"""Explainable AI (XAI) for AIOS v10.7.0.

Decision explanation with factor attribution, confidence scores,
SHAP-like contribution analysis, explanation traceability, and
multi-level detail (brief → detailed → full).

Classes:
    ExplanationLevel — brief / detailed / full
    Factor           — contributing factor with weight
    Explanation      — complete explanation with factors and confidence
    ExplainableAI    — full XAI engine with multi-level explanations
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExplanationLevel(str, Enum):
    """Explanation detail levels."""

    BRIEF = "brief"
    DETAILED = "detailed"
    FULL = "full"


@dataclass
class Factor:
    """Contributing factor with weight."""

    name: str
    weight: float = 0.0  # contribution weight (0..1)
    value: Any = None
    direction: str = "positive"  # positive or negative influence

    def describe(self) -> str:
        """Return human-readable description."""
        arrow = "↑" if self.direction == "positive" else "↓"
        return f"{self.name} ({arrow}, weight={self.weight:.2f})"


@dataclass
class Explanation:
    """Complete explanation with factors and confidence."""

    decision_id: str = ""
    decision: str = ""
    factors: list[Factor] = field(default_factory=list)
    confidence: float = 0.0  # 0..1
    reasoning: str = ""
    level: ExplanationLevel = ExplanationLevel.DETAILED
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Return brief human-readable summary."""
        factor_strs = [f.describe() for f in self.factors]
        return f"Decision '{self.decision}' (confidence={self.confidence:.1%}): {', '.join(factor_strs)}"

    def total_weight(self) -> float:
        """Sum of all factor weights."""
        return sum(f.weight for f in self.factors)


class ExplainableAI:
    """Full XAI engine with multi-level explanations and traceability.

    Features:
    - Multi-level explanations (brief, detailed, full)
    - Factor-based attribution with weights
    - Confidence scoring
    - Explanation traceability (audit trail)
    - Counterfactual reasoning ("what if X were different?")
    - Decision explanation registry
    """

    def __init__(self) -> None:
        self.explanations: dict[str, Explanation] = {}
        self._decision_log: list[dict[str, Any]] = []

    # ── Core Explain ─────────────────────────────────────────────

    def explain(
        self,
        decision_id: str,
        factors: list[str] | None = None,
        weights: list[float] | None = None,
        decision: str = "",
        confidence: float = 0.0,
        level: ExplanationLevel = ExplanationLevel.DETAILED,
    ) -> Explanation:
        """Create an explanation for a decision.

        Backward-compatible: also accepts simple string factor list.
        """
        # Build factor objects
        factor_objs: list[Factor] = []
        if factors:
            for i, name in enumerate(factors):
                weight = (
                    weights[i] if weights and i < len(weights) else 1.0 / len(factors)
                )
                direction = "positive" if weight >= 0 else "negative"
                factor_objs.append(
                    Factor(name=name, weight=abs(weight), direction=direction)
                )

        explanation = Explanation(
            decision_id=decision_id,
            decision=decision or decision_id,
            factors=factor_objs,
            confidence=confidence,
            level=level,
            reasoning=self._build_reasoning(factor_objs, decision, level),
        )
        self.explanations[decision_id] = explanation
        self._decision_log.append(
            {"id": decision_id, "decision": decision, "timestamp": time.time()}
        )
        return explanation

    def explain_with_values(
        self,
        decision_id: str,
        factors: dict[str, tuple[Any, float]],
        decision: str = "",
        confidence: float = 0.0,
    ) -> Explanation:
        """Create explanation with factor values and weights.

        factors: {name: (value, weight)}
        """
        factor_objs = []
        for name, (value, weight) in factors.items():
            direction = "positive" if weight >= 0 else "negative"
            factor_objs.append(
                Factor(name=name, weight=abs(weight), value=value, direction=direction)
            )
        explanation = Explanation(
            decision_id=decision_id,
            decision=decision,
            factors=factor_objs,
            confidence=confidence,
            reasoning=self._build_reasoning(
                factor_objs, decision, ExplanationLevel.DETAILED
            ),
        )
        self.explanations[decision_id] = explanation
        return explanation

    # ── Level-based Retrieval ────────────────────────────────────

    def get_explanation(
        self, decision_id: str, level: ExplanationLevel = ExplanationLevel.DETAILED
    ) -> str:
        """Get explanation at specified detail level."""
        exp = self.explanations.get(decision_id)
        if exp is None:
            return "No explanation available"

        if level == ExplanationLevel.BRIEF:
            return f"{exp.decision}: {', '.join(f.name for f in exp.factors)}"
        if level == ExplanationLevel.DETAILED:
            return f"{exp.decision} (confidence={exp.confidence:.1%}): {exp.reasoning}"
        # FULL level
        lines = [f"Decision: {exp.decision}", f"Confidence: {exp.confidence:.1%}"]
        for f in exp.factors:
            lines.append(f"  Factor: {f.describe()}, value={f.value}")
        lines.append(f"Reasoning: {exp.reasoning}")
        return "\n".join(lines)

    # ── Counterfactual ───────────────────────────────────────────

    def counterfactual(
        self, decision_id: str, change_factor: str, new_value: Any
    ) -> str:
        """Generate counterfactual: what if one factor were different?"""
        exp = self.explanations.get(decision_id)
        if exp is None:
            return "No explanation to analyze"
        # Find the factor
        for f in exp.factors:
            if f.name == change_factor:
                new_direction = "negative" if f.direction == "positive" else "positive"
                return (
                    f"If {change_factor} were {new_value} instead of {f.value}, "
                    f"the decision might shift due to {new_direction} influence "
                    f"(original weight={f.weight:.2f})"
                )
        return f"Factor '{change_factor}' not found in explanation"

    # ── Contribution Analysis ────────────────────────────────────

    def top_factors(self, decision_id: str, n: int = 5) -> list[Factor]:
        """Return top N contributing factors."""
        exp = self.explanations.get(decision_id)
        if exp is None:
            return []
        sorted_factors = sorted(exp.factors, key=lambda f: f.weight, reverse=True)
        return sorted_factors[:n]

    def factor_contribution_chart(self, decision_id: str) -> dict[str, float]:
        """Return normalized contribution percentages per factor."""
        exp = self.explanations.get(decision_id)
        if exp is None:
            return {}
        total = exp.total_weight()
        if total == 0:
            return {f.name: 0.0 for f in exp.factors}
        return {f.name: f.weight / total * 100 for f in exp.factors}

    # ── Query ────────────────────────────────────────────────────

    def list_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return all logged decisions."""
        return self._decision_log[-limit:]

    def search_by_factor(self, factor_name: str) -> list[Explanation]:
        """Find all decisions involving a specific factor."""
        results = []
        for exp in self.explanations.values():
            if any(f.name == factor_name for f in exp.factors):
                results.append(exp)
        return results

    # ── Internal ─────────────────────────────────────────────────

    def _build_reasoning(
        self, factors: list[Factor], decision: str, level: ExplanationLevel
    ) -> str:
        """Auto-generate reasoning text from factors."""
        if not factors:
            return f"Decision {decision} was made based on default logic"
        factor_strs = [f.describe() for f in factors]
        return f"Decision {decision} was made because: {', '.join(factor_strs)}"

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "explained_decisions": len(self.explanations),
            "total_factors": sum(len(e.factors) for e in self.explanations.values()),
            "avg_confidence": sum(e.confidence for e in self.explanations.values())
            / len(self.explanations)
            if self.explanations
            else 0.0,
        }
