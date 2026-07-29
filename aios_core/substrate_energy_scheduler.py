"""Energy-Aware Substrate Scheduling (v11.4.0) — policies + AI wiring (v11.7.0).

Policy layer on top of ``SubstrateConvergenceEngine``. Where the engine
balances affinity, efficiency and load, this scheduler optimizes according
to a named POLICY:

- ``min_energy``  — cheapest expected energy among feasible candidates
- ``min_latency`` — fastest health-normalized latency
- ``balanced``    — weighted blend of (normalized) energy and latency
- ``ai_optimized``— argmax of the Q-values learned by the engine's
  SubstrateAIManager from real dispatch outcomes (falls back to
  ``min_energy`` while the Q-table is cold)

Savings are measured per dispatch against the engine's own baseline
selection (``select_optimal_substrate``), so the report answers the
question "how much energy did the policy save compared to the default
router?".
"""

from __future__ import annotations

import time
from typing import Any

__all__ = ["SCHEDULING_POLICIES", "EnergyAwareScheduler", "RollingEnergyBudget"]

# Min health mirror of SubstrateConvergenceEngine.select_optimal_substrate
_MIN_HEALTH = 0.5

#: Supported scheduling policies for plan()/dispatch().
SCHEDULING_POLICIES = ("min_energy", "min_latency", "balanced", "ai_optimized")


class RollingEnergyBudget:
    """Sliding-window energy budget (cost units per window_seconds)."""

    def __init__(self, limit: float, window_seconds: float = 3600.0) -> None:
        if limit <= 0:
            raise ValueError("budget limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.limit = float(limit)
        self.window_seconds = float(window_seconds)
        self._spends: list[tuple[float, float]] = []  # (timestamp, cost)

    def _prune(self) -> None:
        cutoff = time.time() - self.window_seconds
        self._spends = [(ts, cost) for ts, cost in self._spends if ts >= cutoff]

    def spent(self) -> float:
        """Energy spent within the current window."""
        self._prune()
        return sum(cost for _ts, cost in self._spends)

    def remaining(self) -> float:
        """Budget still available in the current window."""
        return max(0.0, self.limit - self.spent())

    def can_afford(self, cost: float) -> bool:
        """True if recording ``cost`` would stay within the budget."""
        return self.spent() + cost <= self.limit

    def record(self, cost: float) -> None:
        """Record an actual energy spend."""
        self._prune()
        self._spends.append((time.time(), float(cost)))

    def to_dict(self) -> dict[str, Any]:
        """Serialize budget state for JSON APIs."""
        return {
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "spent": round(self.spent(), 4),
            "remaining": round(self.remaining(), 4),
        }


class EnergyAwareScheduler:
    """Energy-optimal routing policy for a SubstrateConvergenceEngine."""

    def __init__(
        self,
        engine: Any,
        latency_budget_ms: float | None = None,
        energy_budget: RollingEnergyBudget | None = None,
        policy: str = "min_energy",
        balanced_weights: tuple[float, float] = (0.5, 0.5),
    ) -> None:
        self._check_policy(policy)
        self.engine = engine
        self.latency_budget_ms = latency_budget_ms
        self.energy_budget = energy_budget
        self.policy = policy
        self.balanced_weights = balanced_weights
        self._dispatches: list[dict[str, Any]] = []

    @staticmethod
    def _check_policy(policy: str) -> None:
        if policy not in SCHEDULING_POLICIES:
            raise ValueError(f"unknown scheduling policy {policy!r} (one of {', '.join(SCHEDULING_POLICIES)})")

    def _q_value(self, category: str, substrate: str) -> float:
        """Learned Q-value for (category, substrate) from the engine AI manager."""
        return self.engine.ai_manager.q_table.get(category, {}).get(substrate, 0.0)

    def _select(
        self,
        candidates: list[dict[str, Any]],
        category: str,
        policy: str,
    ) -> dict[str, Any] | None:
        """Pick the winning candidate under the given policy (None if none)."""
        if not candidates:
            return None

        if policy == "min_latency":
            return min(
                candidates,
                key=lambda c: (c["expected_latency_ms"], c["expected_energy"], c["substrate"]),
            )

        if policy == "balanced":
            w_energy, w_latency = self.balanced_weights
            max_energy = max(c["expected_energy"] for c in candidates) or 1.0
            max_latency = max(c["expected_latency_ms"] for c in candidates) or 1.0

            def score(c: dict[str, Any]) -> tuple[float, float, str]:
                blended = w_energy * (c["expected_energy"] / max_energy) + w_latency * (
                    c["expected_latency_ms"] / max_latency
                )
                return (blended, c["expected_energy"], c["substrate"])

            return min(candidates, key=score)

        if policy == "ai_optimized":
            # argmax learned Q for this category; a cold Q-table is all
            # zeros, in which case the min_energy tie-break below wins.
            return min(
                candidates,
                key=lambda c: (
                    -self._q_value(category, c["substrate"]),
                    c["expected_energy"],
                    c["substrate"],
                ),
            )

        # min_energy (default)
        return min(
            candidates,
            key=lambda c: (
                c["expected_energy"],
                -c["efficiency_gflops_per_watt"],
                c["expected_latency_ms"],
                c["substrate"],
            ),
        )

    # ------------------------------------------------------------------
    # Candidate evaluation
    # ------------------------------------------------------------------

    def candidates(self, task: dict[str, Any]) -> list[dict[str, Any]]:
        """Active, healthy substrates with estimated energy and latency.

        Affinity narrows the candidate set when at least one active
        substrate lists the task category (mirrors the engine's affinity
        step); otherwise every active substrate is a candidate.
        """
        active = [s for s in self.engine.substrates.values() if s["active"] and s["health"] > _MIN_HEALTH]
        if not active:
            return []

        category = task.get("category", "general")
        affinity = [s for s in active if category in s.get("task_affinity", [])]
        pool = affinity if affinity else active

        units = task.get("compute_units", 1)
        result: list[dict[str, Any]] = []
        for sub in pool:
            # Degraded substrates execute slower: normalize by health.
            expected_latency = sub["latency_base_ms"] / max(sub["health"], 0.05)
            result.append(
                {
                    "substrate": sub["type"],
                    "expected_energy": round(units * sub["energy_cost_per_unit"], 6),
                    "expected_latency_ms": round(expected_latency, 4),
                    "efficiency_gflops_per_watt": sub["efficiency_gflops_per_watt"],
                    "health": sub["health"],
                    "capacity_available": sub["capacity"] - sub["current_load"],
                }
            )
        return result

    def plan(self, task: dict[str, Any], policy: str | None = None) -> dict[str, Any]:
        """Dry-run routing decision for a task (nothing is executed).

        Args:
            task: task dict (category, compute_units, id...).
            policy: override for the scheduler's default policy.

        Returns:
            Plan dict: selected substrate, expected energy/latency, the
            engine baseline choice, and any constraint violations.
        """
        policy = policy or self.policy
        self._check_policy(policy)
        task_id = task.get("id", "task")
        category = task.get("category", "general")
        candidates = self.candidates(task)
        violations: list[str] = []

        excluded_by_latency = 0
        if self.latency_budget_ms is not None:
            within = [c for c in candidates if c["expected_latency_ms"] <= self.latency_budget_ms]
            excluded_by_latency = len(candidates) - len(within)
            candidates = within

        selected: dict[str, Any] | None = None
        if candidates:
            chosen = self._select(candidates, category, policy)
            if self.energy_budget and not self.energy_budget.can_afford(chosen["expected_energy"]):
                violations.append("energy_budget_exceeded")
            else:
                selected = chosen
        else:
            violations.append("no_substrate_within_constraints")

        # Baseline: what the engine itself would pick (for savings accounting).
        baseline = self.engine.select_optimal_substrate(task)
        baseline_sub = self.engine.substrates.get(baseline, {})
        units = task.get("compute_units", 1)
        baseline_energy = round(units * baseline_sub.get("energy_cost_per_unit", 0.0), 6)

        result = {
            "task_id": task_id,
            "policy": policy,
            "selected_substrate": selected["substrate"] if selected else None,
            "expected_energy": selected["expected_energy"] if selected else None,
            "expected_latency_ms": selected["expected_latency_ms"] if selected else None,
            "baseline_substrate": baseline,
            "baseline_energy": baseline_energy,
            "expected_savings": (round(baseline_energy - selected["expected_energy"], 6) if selected else 0.0),
            "constraint_violation": bool(violations),
            "violations": violations,
            "excluded_by_latency_budget": excluded_by_latency,
            "candidates_count": len(self.candidates(task)),
        }
        if policy == "ai_optimized" and selected:
            result["ai_q_value"] = round(self._q_value(category, selected["substrate"]), 6)
        return result

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def dispatch(self, task: dict[str, Any], policy: str | None = None) -> dict[str, Any]:
        """Route a task through the energy-aware policy and execute it.

        On constraint violation the dispatch degrades gracefully to the
        engine's own routing (policy="fallback"): progress beats purity —
        a task that cannot fit the energy policy still runs.
        """
        policy = policy or self.policy
        decision = self.plan(task, policy=policy)

        if decision["constraint_violation"] or decision["selected_substrate"] is None:
            result = self.engine.execute_substrate_task(task)
            result["policy"] = "fallback"
            result["violations"] = decision["violations"]
        else:
            steered = {**task, "preferred_type": decision["selected_substrate"]}
            result = self.engine.execute_substrate_task(steered)
            result["policy"] = "energy_aware"
            result["violations"] = []

        result["scheduling_policy"] = policy
        actual_cost = result.get("energy_cost", 0.0)
        savings = max(0.0, decision["baseline_energy"] - actual_cost)
        if self.energy_budget:
            self.energy_budget.record(actual_cost)

        result["energy_saved_vs_baseline"] = round(savings, 6)
        self._dispatches.append(
            {
                "task_id": decision["task_id"],
                "policy": result["policy"],
                "scheduling_policy": policy,
                "substrate": result.get("selected_substrate"),
                "energy_cost": actual_cost,
                "energy_saved": round(savings, 6),
                "timestamp": time.time(),
            }
        )
        return result

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def report(self) -> dict[str, Any]:
        """Aggregate energy/savings report across all dispatches."""
        spent = sum(d["energy_cost"] for d in self._dispatches)
        saved = sum(d["energy_saved"] for d in self._dispatches)
        fallbacks = sum(1 for d in self._dispatches if d["policy"] == "fallback")
        per_policy: dict[str, int] = {}
        for dispatch in self._dispatches:
            name = dispatch.get("scheduling_policy", self.policy)
            per_policy[name] = per_policy.get(name, 0) + 1
        return {
            "dispatches": len(self._dispatches),
            "fallback_dispatches": fallbacks,
            "energy_spent_total": round(spent, 4),
            "energy_saved_vs_baseline": round(saved, 4),
            "savings_pct": round(100.0 * saved / (spent + saved), 2) if (spent + saved) > 0 else 0.0,
            "policy": self.policy,
            "policy_dispatches": per_policy,
            "latency_budget_ms": self.latency_budget_ms,
            "energy_budget": self.energy_budget.to_dict() if self.energy_budget else None,
        }
