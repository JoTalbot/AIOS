"""AIOS ML Planner Scorer v4.0.0

Machine Learning based plan quality scoring and optimization.
Uses heuristic features + placeholder ML model, with cross-validation,
feature importance, batch scoring, A/B testing comparison, and
training data collection for future real model integration.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from typing import Any

from .planner import Plan, Planner
from .storage import Database

__all__ = ["MLPlannerScorer"]


class MLPlannerScorer:
    """Scores and optimizes plans using ML-inspired heuristics.

    Features:
    - ML-enhanced plan scoring with feature extraction
    - Feature importance ranking for interpretability
    - Cross-validation scoring across multiple planners
    - Batch scoring for large plan sets
    - A/B testing comparison between plans
    - Training data collection for real model integration
    - Score history and regression detection
    """

    def __init__(self, db: Database | None = None):
        """Initialize MLPlannerScorer."""
        self.db = db
        self.version = "4.0.0"
        self._model_loaded = False
        self._score_history: list[dict[str, Any]] = []
        self._training_data: list[dict[str, Any]] = []
        self._feature_importance: dict[str, float] = {
            "parallelism": 0.25,
            "avg_dependencies": 0.20,
            "step_diversity": 0.15,
            "has_evolution": 0.10,
            "has_memory": 0.05,
            "plan_length": 0.10,
            "goal_coverage": 0.10,
            "novelty": 0.05,
        }

    # ------------------------------------------------------------------
    # Core scoring
    # ------------------------------------------------------------------

    def score_plan(self, plan: Plan, planner: Planner) -> dict[str, Any]:
        """Return ML-enhanced score for a plan."""
        start_time = time.time()
        base_score = planner.score_plan(plan)

        ml_features = self._extract_features(plan, planner)
        ml_adjustment = self._predict_adjustment(ml_features)

        final_score = round(base_score["score"] * (0.7 + 0.3 * ml_adjustment), 3)

        result = {
            **base_score,
            "ml_score": final_score,
            "ml_features": ml_features,
            "ml_adjustment": round(ml_adjustment, 3),
            "model_version": self.version,
            "score_latency_ms": round((time.time() - start_time) * 1000.0, 3),
        }

        # Archive to history and training data
        self._score_history.append(result)
        self._training_data.append(
            {
                "features": ml_features,
                "base_score": base_score["score"],
                "ml_score": final_score,
                "adjustment": ml_adjustment,
            }
        )

        return result

    def _extract_features(self, plan: Plan, planner: Planner) -> dict[str, float]:
        """Extract features for ML model."""
        layers = planner.get_execution_layers(plan)
        total_steps = len(plan.steps)

        # Goal coverage: how many steps address goals
        goal_steps = sum(1 for s in plan.steps if hasattr(s, "goal") and s.goal)
        goal_coverage = goal_steps / max(1, total_steps)

        # Novelty: fraction of unique step types
        unique_types = len({s.step_type for s in plan.steps})

        return {
            "parallelism": len(layers) / max(1, total_steps),
            "avg_dependencies": sum(len(s.dependencies) for s in plan.steps)
            / max(1, total_steps),
            "step_diversity": unique_types / 10.0,
            "has_evolution": any(s.step_type == "evolve" for s in plan.steps),
            "has_memory": any(s.step_type == "memory" for s in plan.steps),
            "plan_length": min(total_steps / 20.0, 1.0),
            "goal_coverage": goal_coverage,
            "novelty": unique_types / max(1, total_steps),
        }

    def _predict_adjustment(self, features: dict[str, float]) -> float:
        """Simulate ML prediction using weighted feature importance."""
        score = 0.0
        for feat_name, importance in self._feature_importance.items():
            feat_val = features.get(feat_name, 0)
            # For boolean features (0/1), use importance * val
            if isinstance(feat_val, bool):
                score += importance * (1.0 if feat_val else 0.0)
            elif feat_name == "avg_dependencies":
                # Lower dependencies is better
                score += importance * (1 - min(feat_val, 1.0))
            elif feat_name == "parallelism":
                # Lower parallelism (more sequential) is slightly better for some plans
                score += importance * (1 - feat_val)
            else:
                score += importance * min(feat_val, 1.0)

        # Shift to 0.6–1.4 range
        return max(0.6, min(1.4, score + 0.8))

    # ------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------

    def get_feature_importance(self) -> dict[str, float]:
        """Return current feature importance rankings."""
        return dict(self._feature_importance)

    def set_feature_importance(self, importance: dict[str, float]) -> None:
        """Override feature importance weights."""
        self._feature_importance.update(importance)

    def rank_features(self) -> list[tuple[str, float]]:
        """Return features sorted by importance (descending)."""
        return sorted(
            self._feature_importance.items(),
            key=lambda x: x[1],
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Cross-validation
    # ------------------------------------------------------------------

    def cross_validate(
        self,
        plan: Plan,
        planners: Sequence[Planner],
    ) -> dict[str, Any]:
        """Score *plan* across multiple planners for robustness estimation.

        Returns mean, std, and individual scores.
        """
        scores: list[float] = []
        individual: list[dict[str, Any]] = []

        for planner in planners:
            result = self.score_plan(plan, planner)
            scores.append(result["ml_score"])
            individual.append(result)

        if not scores:
            return {"mean_score": 0.0, "std_score": 0.0, "individual_scores": []}

        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = math.sqrt(variance)

        return {
            "mean_score": round(mean, 3),
            "std_score": round(std, 3),
            "min_score": round(min(scores), 3),
            "max_score": round(max(scores), 3),
            "individual_scores": scores,
            "num_planners": len(planners),
            "confidence": round(1 - std / max(0.001, mean), 3),
        }

    # ------------------------------------------------------------------
    # Batch scoring
    # ------------------------------------------------------------------

    def batch_score(
        self,
        plans: Sequence[Plan],
        planner: Planner,
    ) -> list[dict[str, Any]]:
        """Score multiple plans efficiently."""
        results: list[dict[str, Any]] = []
        for plan in plans:
            result = self.score_plan(plan, planner)
            results.append(result)
        return results

    def rank_plans(
        self,
        plans: Sequence[Plan],
        planner: Planner,
    ) -> list[tuple[Plan, float]]:
        """Rank plans by ML score (descending)."""
        scores = self.batch_score(plans, planner)
        ranked = sorted(
            zip(plans, scores),
            key=lambda x: x[1]["ml_score"],
            reverse=True,
        )
        return [(plan, result["ml_score"]) for plan, result in ranked]

    # ------------------------------------------------------------------
    # A/B testing
    # ------------------------------------------------------------------

    def compare_plans(
        self,
        plan_a: Plan,
        plan_b: Plan,
        planner: Planner,
    ) -> dict[str, Any]:
        """A/B test comparison between two plans."""
        score_a = self.score_plan(plan_a, planner)
        score_b = self.score_plan(plan_b, planner)

        ml_a = score_a["ml_score"]
        ml_b = score_b["ml_score"]
        delta = ml_a - ml_b

        return {
            "plan_a_ml_score": ml_a,
            "plan_b_ml_score": ml_b,
            "delta": round(delta, 3),
            "winner": "A" if delta > 0 else "B" if delta < 0 else "tie",
            "relative_improvement": round(delta / max(0.001, abs(ml_b)) * 100, 2),
            "feature_comparison": {
                "parallelism_delta": round(
                    score_a["ml_features"]["parallelism"]
                    - score_b["ml_features"]["parallelism"],
                    3,
                ),
                "diversity_delta": round(
                    score_a["ml_features"]["step_diversity"]
                    - score_b["ml_features"]["step_diversity"],
                    3,
                ),
                "goal_coverage_delta": round(
                    score_a["ml_features"]["goal_coverage"]
                    - score_b["ml_features"]["goal_coverage"],
                    3,
                ),
            },
        }

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------

    def optimize_plan(self, plan: Plan, planner: Planner) -> dict[str, Any]:
        """Suggest optimizations for the plan."""
        score_result = self.score_plan(plan, planner)

        suggestions: list[str] = []

        features = score_result["ml_features"]

        if features["parallelism"] > 0.6:
            suggestions.append("Consider adding more parallel steps")
        if features["avg_dependencies"] > 0.7:
            suggestions.append("Reduce dependency density for better parallelism")
        if not features["has_evolution"]:
            suggestions.append("Add evolution step for self-improvement")
        if not features["has_memory"]:
            suggestions.append("Add memory step for persistent state")
        if features["goal_coverage"] < 0.5:
            suggestions.append(
                "Increase goal coverage — more steps should address stated goals"
            )
        if features["novelty"] < 0.2:
            suggestions.append("Add diverse step types for novelty")
        if features["plan_length"] > 0.8:
            suggestions.append("Consider simplifying the plan to reduce execution risk")

        return {
            "original_score": score_result["score"],
            "ml_score": score_result["ml_score"],
            "suggestions": suggestions,
            "optimized": len(suggestions) > 0,
            "feature_importance_ranking": self.rank_features()[:3],
        }

    # ------------------------------------------------------------------
    # Training data
    # ------------------------------------------------------------------

    def collect_training_data(self) -> list[dict[str, Any]]:
        """Return accumulated training data for future model training."""
        return list(self._training_data)

    def clear_training_data(self) -> int:
        """Clear training data buffer. Returns items cleared."""
        count = len(self._training_data)
        self._training_data.clear()
        return count

    # ------------------------------------------------------------------
    # Score history
    # ------------------------------------------------------------------

    def get_score_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent score history."""
        return self._score_history[-limit:]

    def detect_regression(
        self, window: int = 10, threshold: float = 0.15
    ) -> dict[str, Any]:
        """Detect score regression in recent history.

        Returns regression info if average recent scores drop below
        (1 - threshold) * average older scores.
        """
        if len(self._score_history) < 2 * window:
            return {"regression_detected": False, "reason": "Insufficient history"}

        recent = self._score_history[-window:]
        older = self._score_history[-2 * window : -window]

        avg_recent = sum(r["ml_score"] for r in recent) / window
        avg_older = sum(r["ml_score"] for r in older) / window

        regression = avg_recent < avg_older * (1 - threshold)

        return {
            "regression_detected": regression,
            "avg_recent": round(avg_recent, 3),
            "avg_older": round(avg_older, 3),
            "delta": round(avg_recent - avg_older, 3),
            "threshold": threshold,
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "version": self.version,
            "model_loaded": self._model_loaded,
            "type": "heuristic+ml-placeholder",
            "score_history_size": len(self._score_history),
            "training_data_size": len(self._training_data),
            "feature_importance": self._feature_importance,
        }
