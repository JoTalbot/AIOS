"""Energy-Aware Substrate Scheduling (v11.4.0).

Policy layer on top of ``SubstrateConvergenceEngine``. Where the engine
balances affinity, efficiency and load, this scheduler optimizes
primarily for ENERGY: among the substrates that satisfy the task
constraints it picks the cheapest expected energy cost, subject to an
optional latency budget and an optional rolling energy budget.

Savings are measured per dispatch against the engine's own baseline
selection (``select_optimal_substrate``), so the report answers the
question "how much energy did the policy save compared to the default
router?".
"""

from __future__ import annotations

import time
from typing import Any

__all__ = ["EnergyAwareScheduler", "RollingEnergyBudget"]

# Min health mirror of SubstrateConvergenceEngine.select_optimal_substrate
_MIN_HEALTH = 0.5


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
    ) -> None:
        self.engine = engine
        self.latency_budget_ms = latency_budget_ms
        self.energy_budget = energy_budget
        self._dispatches: list[dict[str, Any]] = []

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

    def plan(self, task: dict[str, Any]) -> dict[str, Any]:
        """Dry-run routing decision for a task (nothing is executed).

        Returns:
            Plan dict: selected substrate, expected energy/latency, the
            engine baseline choice, and any constraint violations.
        """
        task_id = task.get("id", "task")
        candidates = self.candidates(task)
        violations: list[str] = []

        excluded_by_latency = 0
        if self.latency_budget_ms is not None:
            within = [c for c in candidates if c["expected_latency_ms"] <= self.latency_budget_ms]
            excluded_by_latency = len(candidates) - len(within)
            candidates = within

        selected: dict[str, Any] | None = None
        if candidates:
            cheapest = min(
                candidates,
                key=lambda c: (
                    c["expected_energy"],
                    -c["efficiency_gflops_per_watt"],
                    c["expected_latency_ms"],
                    c["substrate"],
                ),
            )
            if self.energy_budget and not self.energy_budget.can_afford(cheapest["expected_energy"]):
                violations.append("energy_budget_exceeded")
            else:
                selected = cheapest
        else:
            violations.append("no_substrate_within_constraints")

        # Baseline: what the engine itself would pick (for savings accounting).
        baseline = self.engine.select_optimal_substrate(task)
        baseline_sub = self.engine.substrates.get(baseline, {})
        units = task.get("compute_units", 1)
        baseline_energy = round(units * baseline_sub.get("energy_cost_per_unit", 0.0), 6)

        return {
            "task_id": task_id,
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

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def dispatch(self, task: dict[str, Any]) -> dict[str, Any]:
        """Route a task through the energy-aware policy and execute it.

        On constraint violation the dispatch degrades gracefully to the
        engine's own routing (policy="fallback"): progress beats purity —
        a task that cannot fit the energy policy still runs.
        """
        decision = self.plan(task)

        if decision["constraint_violation"] or decision["selected_substrate"] is None:
            result = self.engine.execute_substrate_task(task)
            result["policy"] = "fallback"
            result["violations"] = decision["violations"]
        else:
            steered = {**task, "preferred_type": decision["selected_substrate"]}
            result = self.engine.execute_substrate_task(steered)
            result["policy"] = "energy_aware"
            result["violations"] = []

        actual_cost = result.get("energy_cost", 0.0)
        savings = max(0.0, decision["baseline_energy"] - actual_cost)
        if self.energy_budget:
            self.energy_budget.record(actual_cost)

        result["energy_saved_vs_baseline"] = round(savings, 6)
        self._dispatches.append(
            {
                "task_id": decision["task_id"],
                "policy": result["policy"],
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
        return {
            "dispatches": len(self._dispatches),
            "fallback_dispatches": fallbacks,
            "energy_spent_total": round(spent, 4),
            "energy_saved_vs_baseline": round(saved, 4),
            "savings_pct": round(100.0 * saved / (spent + saved), 2) if (spent + saved) > 0 else 0.0,
            "latency_budget_ms": self.latency_budget_ms,
            "energy_budget": self.energy_budget.to_dict() if self.energy_budget else None,
        }
