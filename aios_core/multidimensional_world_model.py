"""Multi-Dimensional Universal World & Predictive Simulation Model for AIOS Horizon 7.0.

Provides counterfactual state trajectory forecasting, Monte Carlo rollouts across
system compute resources, multi-agent economic impact, environmental safety risk,
branching scenario analysis, confidence intervals, and historical state tracking.
"""

import math
import random
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = ["MultiDimensionalWorldModel"]


class MultiDimensionalWorldModel:
    """Predictive Multi-Dimensional Simulation Engine.

    Features:
    - Monte Carlo counterfactual trajectory simulation
    - Branching scenario analysis with divergence tracking
    - Multi-agent economic and resource impact modeling
    - Environmental safety risk scoring
    - Confidence interval computation via bootstrap resampling
    - Historical state archival for retrospection
    - Risk-weighted action plan scoring
    """

    def __init__(self, simulation_horizon_steps: int = 10, num_rollouts: int = 5):
        """Initialize MultiDimensionalWorldModel."""
        self.simulation_horizon_steps = simulation_horizon_steps
        self.num_rollouts = num_rollouts
        self.rollouts_count = 0
        self._history: List[dict[str, Any]] = []
        self._branch_cache: Dict[str, List[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Core simulation
    # ------------------------------------------------------------------

    def simulate_action_impact(
        self,
        action_plan: dict[str, Any],
        initial_environment_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run predictive Monte Carlo counterfactual simulation for proposed action plan."""
        start_time = time.time()
        env_state = dict(
            initial_environment_state
            or {
                "cpu_load": 0.15,
                "memory_mb": 512,
                "system_health": 1.0,
                "econ_cost_usd": 0.0,
                "risk_score": 0.0,
            }
        )

        trajectory: List[dict[str, Any]] = []
        projected_failures = 0

        action_complexity = action_plan.get("complexity", 1.0)
        action_scale = action_plan.get("scale", 1)
        action_risk = action_plan.get("risk_factor", 0.1)

        for step in range(self.simulation_horizon_steps):
            delta_cpu = (action_complexity * 0.02) + random.uniform(-0.01, 0.02)
            delta_mem = (action_scale * 16) + random.randint(0, 10)
            delta_cost = action_complexity * 0.005
            delta_risk = action_risk * 0.01 * random.uniform(0.5, 1.5)

            env_state["cpu_load"] = min(1.0, env_state["cpu_load"] + delta_cpu)
            env_state["memory_mb"] = env_state["memory_mb"] + delta_mem
            env_state["econ_cost_usd"] = round(env_state["econ_cost_usd"] + delta_cost, 4)
            env_state["risk_score"] = min(1.0, round(env_state["risk_score"] + delta_risk, 3))

            # Check simulated threshold bounds
            if env_state["cpu_load"] >= 0.95 or env_state["memory_mb"] > 16384:
                projected_failures += 1
                env_state["system_health"] = max(0.0, env_state["system_health"] - 0.2)

            trajectory.append(
                {
                    "step": step + 1,
                    "sim_cpu_load": round(env_state["cpu_load"], 3),
                    "sim_memory_mb": env_state["memory_mb"],
                    "sim_cost_usd": env_state["econ_cost_usd"],
                    "sim_health": round(env_state["system_health"], 2),
                    "sim_risk": env_state["risk_score"],
                }
            )

        self.rollouts_count += 1
        execution_time_ms = round((time.time() - start_time) * 1000.0, 3)

        result = {
            "is_safe_trajectory": projected_failures == 0,
            "projected_failures": projected_failures,
            "final_predicted_state": env_state,
            "simulated_trajectory": trajectory,
            "simulation_steps": self.simulation_horizon_steps,
            "simulation_time_ms": execution_time_ms,
        }

        # Archive to history
        self._history.append(result)
        if len(self._history) > 500:
            self._history = self._history[-500:]

        return result

    # ------------------------------------------------------------------
    # Multi-rollout Monte Carlo
    # ------------------------------------------------------------------

    def monte_carlo_rollout(
        self,
        action_plan: dict[str, Any],
        initial_state: dict[str, Any] | None = None,
        num_rollouts: int | None = None,
    ) -> dict[str, Any]:
        """Execute multiple Monte Carlo rollouts for robustness estimation.

        Returns aggregate statistics across all rollouts including
        confidence intervals for key metrics.
        """
        n = num_rollouts or self.num_rollouts
        results: List[dict[str, Any]] = []

        for i in range(n):
            result = self.simulate_action_impact(action_plan, initial_state)
            results.append(result)

        # Aggregate statistics
        safe_count = sum(1 for r in results if r["is_safe_trajectory"])
        avg_failures = sum(r["projected_failures"] for r in results) / n
        avg_cost = sum(
            r["final_predicted_state"]["econ_cost_usd"] for r in results
        ) / n
        avg_health = sum(
            r["final_predicted_state"]["system_health"] for r in results
        ) / n
        avg_risk = sum(
            r["final_predicted_state"].get("risk_score", 0) for r in results
        ) / n

        # Confidence intervals (bootstrap-style)
        costs = [r["final_predicted_state"]["econ_cost_usd"] for r in results]
        ci_cost = self._compute_ci(costs)
        healths = [r["final_predicted_state"]["system_health"] for r in results]
        ci_health = self._compute_ci(healths)

        return {
            "num_rollouts": n,
            "safe_trajectory_probability": round(safe_count / n, 3),
            "avg_projected_failures": round(avg_failures, 3),
            "avg_econ_cost_usd": round(avg_cost, 4),
            "avg_system_health": round(avg_health, 3),
            "avg_risk_score": round(avg_risk, 3),
            "ci_cost_95": ci_cost,
            "ci_health_95": ci_health,
            "individual_results": results,
        }

    # ------------------------------------------------------------------
    # Branching scenario analysis
    # ------------------------------------------------------------------

    def analyze_branches(
        self,
        base_plan: dict[str, Any],
        variations: Sequence[dict[str, Any]],
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compare multiple branching variations of a base action plan.

        Each variation is simulated independently and compared to the base
        to identify divergence points and relative safety.
        """
        base_result = self.simulate_action_impact(base_plan, initial_state)
        branch_results: List[dict[str, Any]] = []

        for i, variation in enumerate(variations):
            branch_result = self.simulate_action_impact(variation, initial_state)
            # Compute divergence from base
            divergence = self._compute_divergence(base_result, branch_result)
            branch_result["branch_id"] = i
            branch_result["divergence_score"] = divergence
            branch_results.append(branch_result)

        # Rank branches by safety and cost
        ranked = sorted(
            branch_results,
            key=lambda r: (r["projected_failures"], r["final_predicted_state"]["econ_cost_usd"]),
        )

        return {
            "base_result": base_result,
            "branch_results": branch_results,
            "ranked_branch_ids": [r["branch_id"] for r in ranked],
            "best_branch": ranked[0]["branch_id"] if ranked else None,
            "total_branches": len(variations),
        }

    # ------------------------------------------------------------------
    # Risk-weighted scoring
    # ------------------------------------------------------------------

    def score_action_risk(
        self,
        action_plan: dict[str, Any],
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Score an action plan with risk-weighted multi-dimensional analysis.

        Combines resource, economic, and safety risk dimensions into
        a single composite risk score.
        """
        result = self.simulate_action_impact(action_plan, initial_state)
        final = result["final_predicted_state"]

        # Resource risk (CPU + memory pressure)
        resource_risk = max(final["cpu_load"], final["memory_mb"] / 16384)

        # Economic risk (cost exceeding threshold)
        econ_risk = min(1.0, final["econ_cost_usd"] / 100.0)

        # Safety risk
        safety_risk = final.get("risk_score", 0.0)

        # Health penalty
        health_penalty = 1.0 - final["system_health"]

        # Composite risk score (weighted)
        composite_risk = (
            resource_risk * 0.30
            + econ_risk * 0.20
            + safety_risk * 0.35
            + health_penalty * 0.15
        )

        return {
            "action_plan": action_plan,
            "composite_risk_score": round(composite_risk, 3),
            "resource_risk": round(resource_risk, 3),
            "economic_risk": round(econ_risk, 3),
            "safety_risk": round(safety_risk, 3),
            "health_penalty": round(health_penalty, 3),
            "is_acceptable": composite_risk < 0.5,
            "risk_category": (
                "low" if composite_risk < 0.3
                else "medium" if composite_risk < 0.6
                else "high"
            ),
            "simulation_result": result,
        }

    # ------------------------------------------------------------------
    # Confidence intervals
    # ------------------------------------------------------------------

    def _compute_ci(
        self, values: List[float], confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Compute bootstrap confidence interval for *values*."""
        if len(values) < 2:
            return (min(values) if values else 0.0, max(values) if values else 0.0)

        mean = sum(values) / len(values)
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
        # Approximate 95% CI using z=1.96
        z = 1.96
        margin = z * std / math.sqrt(len(values))
        return (round(mean - margin, 4), round(mean + margin, 4))

    # ------------------------------------------------------------------
    # Divergence computation
    # ------------------------------------------------------------------

    def _compute_divergence(
        self, base: dict[str, Any], branch: dict[str, Any]
    ) -> float:
        """Compute divergence score between base and branch trajectories."""
        base_final = base["final_predicted_state"]
        branch_final = branch["final_predicted_state"]

        diffs = []
        for key in ["cpu_load", "memory_mb", "econ_cost_usd", "system_health", "risk_score"]:
            if key in base_final and key in branch_final:
                b_val = base_final[key]
                br_val = branch_final[key]
                if b_val != 0:
                    diffs.append(abs(br_val - b_val) / abs(b_val))
                else:
                    diffs.append(abs(br_val - b_val))

        return round(sum(diffs) / max(1, len(diffs)), 3)

    # ------------------------------------------------------------------
    # Historical tracking
    # ------------------------------------------------------------------

    def get_history(
        self, limit: int = 50, filter_safe: bool | None = None
    ) -> List[dict[str, Any]]:
        """Return recent simulation history, optionally filtered."""
        if filter_safe is True:
            filtered = [r for r in self._history if r["is_safe_trajectory"]]
        elif filter_safe is False:
            filtered = [r for r in self._history if not r["is_safe_trajectory"]]
        else:
            filtered = self._history
        return filtered[-limit:]

    def get_history_stats(self) -> dict[str, Any]:
        """Aggregate statistics across all historical simulations."""
        if not self._history:
            return {"total_simulations": 0}

        safe_count = sum(1 for r in self._history if r["is_safe_trajectory"])
        total = len(self._history)
        avg_failures = sum(r["projected_failures"] for r in self._history) / total

        return {
            "total_simulations": total,
            "safe_simulations": safe_count,
            "unsafe_simulations": total - safe_count,
            "safety_rate": round(safe_count / total, 3),
            "avg_projected_failures": round(avg_failures, 3),
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return statistics dict."""
        return {
            "rollouts_count": self.rollouts_count,
            "simulation_horizon_steps": self.simulation_horizon_steps,
            "num_rollouts": self.num_rollouts,
            "history_size": len(self._history),
        }
