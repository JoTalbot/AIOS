"""Energy-Aware Substrate Scheduling (v11.4.0) — policies + AI wiring (v11.7.0) + batch forecasting (v11.8.0).

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

import json
import time
from pathlib import Path
from typing import Any

from .retention import plan_retention_purge

__all__ = ["SCHEDULING_POLICIES", "EnergyAwareScheduler", "RollingEnergyBudget"]

# Min health mirror of SubstrateConvergenceEngine.select_optimal_substrate
_MIN_HEALTH = 0.5

#: Supported scheduling policies for plan()/dispatch().
SCHEDULING_POLICIES = ("min_energy", "min_latency", "balanced", "ai_optimized")

#: On-disk format tag for persisted rolling-budget configuration (v11.13.0).
BUDGET_FILE_FORMAT = 1


def load_energy_budget(path: str | Path) -> RollingEnergyBudget | None:
    """Load a persisted rolling energy budget (v11.13.0).

    Args:
        path: JSON file written by ``EnergyAwareScheduler.save_budget()``.

    Returns:
        A fresh ``RollingEnergyBudget`` (spend ledger starts empty —
        only the configuration is persisted), or ``None`` when the file
        does not exist.

    Raises:
        ValueError: file exists but is malformed or holds invalid values.
    """
    target = Path(path)
    if not target.exists():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError(f"budget file {target} is not valid JSON") from None
    if not isinstance(data, dict) or data.get("format") != BUDGET_FILE_FORMAT:
        raise ValueError(f"budget file {target} has an unsupported format")
    try:
        limit_value = float(data["limit"])
        window_value = float(data["window_seconds"])
    except KeyError as exc:
        raise ValueError(f"budget file {target} is missing key {exc}") from None
    except (TypeError, ValueError):
        raise ValueError(f"budget file {target} holds non-numeric values") from None
    # Constructor re-validates positivity -> ValueError with a clear message.
    return RollingEnergyBudget(limit=limit_value, window_seconds=window_value)


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

    def pressure(self) -> float:
        """Spent/limit ratio for the current window (v11.14.0).

        May exceed 1.0 after a runtime reconfigure that lowered the
        limit below the current window's spend — alerting must not
        assume the invariant ``spent <= limit``.
        """
        return self.spent() / self.limit

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
            "pressure": round(self.pressure(), 4),
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
        self.auto_throttle_enabled: bool = False
        self.throttle_threshold: float = 0.8
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

    def configure_throttle(
        self,
        enabled: bool = True,
        threshold: float = 0.8,
    ) -> dict[str, Any]:
        """Configure dynamic budget policy auto-throttling (v11.16.0).

        When enabled and energy budget pressure reaches/exceeds threshold,
        dispatches dynamically downgrade to 'min_energy' policy to prevent
        budget exhaustion violations.
        """
        try:
            thresh_val = float(threshold)
        except (TypeError, ValueError):
            raise ValueError("threshold must be a number") from None
        if not 0.0 <= thresh_val <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")

        self.auto_throttle_enabled = bool(enabled)
        self.throttle_threshold = thresh_val
        return {
            "auto_throttle_enabled": self.auto_throttle_enabled,
            "throttle_threshold": self.throttle_threshold,
        }

    def plan(self, task: dict[str, Any], policy: str | None = None) -> dict[str, Any]:
        """Dry-run routing decision for a task (nothing is executed).

        Args:
            task: task dict (category, compute_units, id...).
            policy: override for the scheduler's default policy.

        Returns:
            Plan dict: selected substrate, expected energy/latency, the
            engine baseline choice, and any constraint violations.
        """
        requested_policy = policy or self.policy
        self._check_policy(requested_policy)

        effective_policy = requested_policy
        throttled = False
        if self.auto_throttle_enabled and self.energy_budget is not None:
            if self.energy_budget.pressure() >= self.throttle_threshold:
                effective_policy = "min_energy"
                throttled = True

        policy = effective_policy
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
            "requested_policy": requested_policy,
            "effective_policy": effective_policy,
            "throttled": throttled,
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
    # Batch forecasting (v11.8.0)
    # ------------------------------------------------------------------

    # Hard cap so a forecast call stays cheap even over the wire.
    FORECAST_MAX_TASKS = 1000

    def forecast(self, tasks: list[dict[str, Any]], policy: str | None = None) -> dict[str, Any]:
        """Simulate a batch of dispatches without executing anything.

        Each task is planned in order against the CURRENT engine state;
        the rolling energy budget is projected cumulatively, so a task
        that would be affordable on its own is flagged
        ``projected_budget_exceeded`` once the earlier tasks in the batch
        have consumed the remaining window.

        Nothing is executed, recorded or learned: the dispatch report,
        the rolling budget and the engine history are all untouched.

        Args:
            tasks: ordered list of task dicts (category, compute_units).
            policy: override for the scheduler's default policy.

        Returns:
            Forecast dict: per-task plans with affordability flags and
            the projected window usage after the batch.
        """
        policy = policy or self.policy
        self._check_policy(policy)
        if not isinstance(tasks, list):
            raise ValueError("tasks must be a list of task dicts")
        if len(tasks) > self.FORECAST_MAX_TASKS:
            raise ValueError(f"tasks exceeds the {self.FORECAST_MAX_TASKS}-task forecast limit")
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                raise ValueError(f"tasks[{index}] must be a dict")

        spent_now = self.energy_budget.spent() if self.energy_budget else 0.0
        limit = self.energy_budget.limit if self.energy_budget else None
        projected = 0.0
        plans: list[dict[str, Any]] = []

        for index, task in enumerate(tasks):
            plan = self.plan(task, policy=policy)
            expected = plan["expected_energy"]
            affordable = plan["selected_substrate"] is not None
            violations = list(plan["violations"])
            if affordable and limit is not None and spent_now + projected + expected > limit:
                violations.append("projected_budget_exceeded")
                affordable = False
            if affordable:
                projected += expected
            plans.append(
                {
                    "index": index,
                    "task_id": plan["task_id"],
                    "selected_substrate": plan["selected_substrate"],
                    "expected_energy": expected,
                    "expected_latency_ms": plan["expected_latency_ms"],
                    "affordable": affordable,
                    "violations": violations,
                    "cumulative_energy": round(projected, 6),
                }
            )

        return {
            "policy": policy,
            "tasks_total": len(tasks),
            "tasks_affordable": sum(1 for entry in plans if entry["affordable"]),
            "projected_energy": round(projected, 6),
            "window_spent_now": round(spent_now, 6),
            "window_limit": limit,
            "window_remaining_after": (
                round(max(0.0, limit - spent_now - projected), 6) if limit is not None else None
            ),
            "plans": plans,
        }

    # ------------------------------------------------------------------
    # History replay / drift analysis (v11.11.0)
    # ------------------------------------------------------------------

    def replay(self, records: list[dict[str, Any]], policy: str | None = None) -> dict[str, Any]:
        """Re-plan previously recorded dispatches against the CURRENT state
        (routing-drift analysis, v11.11.0).

        Each record (one row of the v11.9 CSV export, or an equivalent
        dict) is reconstructed into a task — compute units are recovered
        exactly from `recorded energy_cost / substrate cost-per-unit`
        (the same formula dispatch used) — and planned dry-run under the
        given policy. The report compares the recorded substrate/energy
        with what the scheduler would pick NOW: matches, potential
        savings and unknown substrate names.

        Nothing is executed or recorded (plans are dry-runs).

        Args:
            records: up to FORECAST_MAX_TASKS dicts with task_id,
                selected_substrate, energy_cost (category optional).
            policy: override for the scheduler's default policy.

        Returns:
            Drift report dict with per-record comparisons.
        """
        policy = policy or self.policy
        self._check_policy(policy)
        if not isinstance(records, list):
            raise ValueError("records must be a list of dispatch records")
        if len(records) > self.FORECAST_MAX_TASKS:
            raise ValueError(f"records exceeds the {self.FORECAST_MAX_TASKS}-record replay limit")

        rows: list[dict[str, Any]] = []
        unknown: set[str] = set()
        recorded_total = 0.0
        planned_total = 0.0

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(f"records[{index}] must be a dict")
            recorded_sub = str(record.get("selected_substrate", ""))
            try:
                recorded_energy = float(record.get("energy_cost", 0.0) or 0.0)
            except (TypeError, ValueError):
                raise ValueError(f"records[{index}].energy_cost must be a number") from None
            sub_info = self.engine.substrates.get(recorded_sub)
            if sub_info is None and recorded_sub:
                unknown.add(recorded_sub)
            if sub_info and sub_info["energy_cost_per_unit"] > 0:
                units = max(1, round(recorded_energy / sub_info["energy_cost_per_unit"]))
            else:
                units = 1
            try:
                units = int(record.get("compute_units", units) or units)
            except (TypeError, ValueError):
                raise ValueError(f"records[{index}].compute_units must be a number") from None

            task = {
                "id": str(record.get("task_id", f"replay_{index}")),
                "category": str(record.get("category") or "general"),
                "compute_units": units,
            }
            plan = self.plan(task, policy=policy)
            planned_energy = plan["expected_energy"]
            recorded_total += recorded_energy
            if planned_energy is not None:
                planned_total += planned_energy
            rows.append(
                {
                    "index": index,
                    "task_id": task["id"],
                    "recorded_substrate": recorded_sub or None,
                    "recorded_energy": recorded_energy,
                    "planned_substrate": plan["selected_substrate"],
                    "planned_energy": planned_energy,
                    "matching": plan["selected_substrate"] == recorded_sub,
                    "energy_delta": (
                        round(recorded_energy - planned_energy, 6) if planned_energy is not None else None
                    ),
                    "violations": plan["violations"],
                }
            )

        matches = sum(1 for row in rows if row["matching"])
        return {
            "policy": policy,
            "records": len(rows),
            "matching": matches,
            "match_pct": round(100.0 * matches / len(rows), 2) if rows else 0.0,
            "recorded_energy_total": round(recorded_total, 4),
            "planned_energy_total": round(planned_total, 4),
            "potential_savings": round(max(0.0, recorded_total - planned_total), 4),
            "unknown_substrates": sorted(unknown),
            "rows": rows,
        }

    # ------------------------------------------------------------------
    # Policy A/B comparison matrix (v11.12.0)
    # ------------------------------------------------------------------

    def compare_policies(
        self,
        tasks: list[dict[str, Any]],
        policies: list[str] | None = None,
        reference_policy: str | None = None,
    ) -> dict[str, Any]:
        """Forecast the SAME task batch under several policies side by side
        (A/B decision matrix, v11.12.0).

        Each policy gets one dry-run forecast; the matrix rows show
        projected energy, affordable task count and the substrate choice
        per task, plus deltas against the reference policy (the
        scheduler's default unless overridden). Pure dry-run.

        Args:
            tasks: the batch (same validation as forecast()).
            policies: policies to compare (default: all 4).
            reference_policy: delta baseline (default: scheduler policy);
                must be part of the compared set.

        Returns:
            Matrix dict: per-policy stats, deltas vs reference, the
            recommended (lowest-energy) policy name.
        """
        if policies is not None and not isinstance(policies, list):
            raise ValueError("policies must be a list of policy names")
        names = list(dict.fromkeys(policies)) if policies is not None else list(SCHEDULING_POLICIES)
        if not names:
            raise ValueError("policies must be a non-empty list")
        for name in names:
            self._check_policy(name)
        reference = reference_policy or self.policy
        if reference not in names:
            raise ValueError(f"reference policy {reference!r} must be one of the compared policies")

        matrix: dict[str, Any] = {}
        for name in names:
            projection = self.forecast(tasks, policy=name)
            matrix[name] = {
                "tasks_affordable": projection["tasks_affordable"],
                "projected_energy": projection["projected_energy"],
                "substrate_choices": [entry["selected_substrate"] for entry in projection["plans"]],
            }

        ref = matrix[reference]
        totals = len(ref["substrate_choices"])
        for stats in matrix.values():
            stats["energy_delta_vs_reference"] = round(stats["projected_energy"] - ref["projected_energy"], 6)
            overlap = sum(
                1
                for chosen, base in zip(stats["substrate_choices"], ref["substrate_choices"], strict=True)
                if chosen == base
            )
            stats["choice_overlap_vs_reference_pct"] = round(100.0 * overlap / totals, 2) if totals else 0.0

        recommended = min(
            names,
            key=lambda n: (matrix[n]["projected_energy"], -matrix[n]["tasks_affordable"], n != reference, n),
        )
        return {
            "tasks_total": len(tasks),
            "policies": names,
            "reference_policy": reference,
            "recommended_policy": recommended,
            "matrix": matrix,
        }

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def report(self, window_seconds: float | None = None) -> dict[str, Any]:
        """Aggregate energy/savings report across dispatches.

        Args:
            window_seconds: optional sliding window (v11.10.0) — only
                dispatches newer than now-window are aggregated. Must be
                positive. The rolling budget, being window-based already,
                always reflects its own window regardless of this filter.
        """
        if window_seconds is not None and window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        dispatches = self._dispatches
        if window_seconds is not None:
            cutoff = time.time() - window_seconds
            dispatches = [d for d in dispatches if d["timestamp"] >= cutoff]

        spent = sum(d["energy_cost"] for d in dispatches)
        saved = sum(d["energy_saved"] for d in dispatches)
        fallbacks = sum(1 for d in dispatches if d["policy"] == "fallback")
        per_policy: dict[str, int] = {}
        for dispatch in dispatches:
            name = dispatch.get("scheduling_policy", self.policy)
            per_policy[name] = per_policy.get(name, 0) + 1
        return {
            "dispatches": len(dispatches),
            "fallback_dispatches": fallbacks,
            "energy_spent_total": round(spent, 4),
            "energy_saved_vs_baseline": round(saved, 4),
            "savings_pct": round(100.0 * saved / (spent + saved), 2) if (spent + saved) > 0 else 0.0,
            "policy": self.policy,
            "policy_dispatches": per_policy,
            "window_seconds": window_seconds,
            "latency_budget_ms": self.latency_budget_ms,
            "energy_budget": self.energy_budget.to_dict() if self.energy_budget else None,
        }

    # ------------------------------------------------------------------
    # Dispatches retention (v11.14.0)
    # ------------------------------------------------------------------

    def preview_purge_dispatches(
        self,
        keep_last: int | None = None,
        older_than_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Dry-run a scheduler-dispatch purge (mirrors the engine purge).

        Same retention semantics as the v11.13 engine history purge —
        a record survives when within the newest ``keep_last`` entries
        OR newer than the age cutoff. Nothing is removed.
        """
        cutoff, protected_count, removed = plan_retention_purge(self._dispatches, keep_last, older_than_seconds)
        removed_set = set(removed)
        remaining = [d for i, d in enumerate(self._dispatches) if i not in removed_set]
        return {
            "dry_run": True,
            "total_dispatches": len(self._dispatches),
            "would_remove": len(removed),
            "would_remain": len(remaining),
            "protected_by_keep_last": protected_count,
            "keep_last": keep_last,
            "older_than_seconds": older_than_seconds,
            "cutoff_timestamp": cutoff,
            "oldest_remaining_timestamp": min((d.get("timestamp", 0.0) for d in remaining), default=None),
        }

    def purge_dispatches(
        self,
        keep_last: int | None = None,
        older_than_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Irreversibly delete scheduler dispatch records.

        Same selection as preview_purge_dispatches() — always dry-run
        first. The rolling budget, being ledger-based, is NOT affected:
        purging history never refunds spend.
        """
        cutoff, protected_count, removed = plan_retention_purge(self._dispatches, keep_last, older_than_seconds)
        removed_set = set(removed)
        self._dispatches = [d for i, d in enumerate(self._dispatches) if i not in removed_set]
        return {
            "dry_run": False,
            "removed": len(removed),
            "remaining": len(self._dispatches),
            "protected_by_keep_last": protected_count,
            "keep_last": keep_last,
            "older_than_seconds": older_than_seconds,
            "cutoff_timestamp": cutoff,
            "purged_at": time.time(),
        }

    # ------------------------------------------------------------------
    # Runtime budget reconfiguration + persistence (v11.13.0)
    # ------------------------------------------------------------------

    def configure_budget(self, limit: float, window_seconds: float | None = None) -> dict[str, Any]:
        """Replace the rolling energy budget while the scheduler is live.

        Spends still inside the NEW window are carried into the new
        budget, so reconfiguring can never silently reset the window
        accounting (a shorter window naturally expires old spends on the
        next prune).

        Args:
            limit: new budget limit in cost units (must be positive).
            window_seconds: new window (default: keep the current one,
                or 3600 when no budget was configured).

        Returns:
            Report dict with the old/new budget state and how many
            spends were carried over.
        """
        try:
            limit_value = float(limit)
        except (TypeError, ValueError):
            raise ValueError("budget limit must be a number") from None
        if limit_value <= 0:
            raise ValueError("budget limit must be positive")
        if window_seconds is None:
            window_value = self.energy_budget.window_seconds if self.energy_budget else 3600.0
        else:
            try:
                window_value = float(window_seconds)
            except (TypeError, ValueError):
                raise ValueError("window_seconds must be a number") from None
            if window_value <= 0:
                raise ValueError("window_seconds must be positive")

        old_state = self.energy_budget.to_dict() if self.energy_budget else None
        new_budget = RollingEnergyBudget(limit=limit_value, window_seconds=window_value)
        carried = 0
        carried_cost = 0.0
        if self.energy_budget is not None:
            cutoff = time.time() - window_value
            for ts, cost in self.energy_budget._spends:
                if ts >= cutoff:
                    new_budget._spends.append((ts, cost))
                    carried += 1
                    carried_cost += cost
        self.energy_budget = new_budget
        return {
            "old": old_state,
            "new": new_budget.to_dict(),
            "carried_spends": carried,
            "carried_cost": round(carried_cost, 6),
        }

    def save_budget(self, path: str | Path) -> dict[str, Any]:
        """Persist the rolling-budget configuration as JSON (v11.13.0).

        Only the configuration (limit/window) is written — the live
        spend ledger stays in memory. Load with load_energy_budget().

        Raises:
            ValueError: scheduler has no energy budget configured.
        """
        if self.energy_budget is None:
            raise ValueError("scheduler has no energy budget configured")
        payload = {
            "format": BUDGET_FILE_FORMAT,
            "limit": self.energy_budget.limit,
            "window_seconds": self.energy_budget.window_seconds,
            "saved_at": time.time(),
        }
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

    def export_forecast_metrics(
        self,
        tasks: list[dict[str, Any]],
        policy: str | None = None,
    ) -> dict[str, Any]:
        """Convert forecast simulation into Prometheus gauge metrics dict (v11.17.0)."""
        fc = self.forecast(tasks, policy=policy)
        return {
            "aios_forecast_tasks_total": fc["tasks_total"],
            "aios_forecast_affordable_tasks": fc["tasks_affordable"],
            "aios_forecast_projected_energy": fc["projected_energy"],
            "aios_forecast_window_limit": fc["window_limit"] or 0.0,
        }

    def recommend_optimal_policy(
        self,
        tasks_sample: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Recommend the optimal policy for workload sample (v11.17.0).

        If no tasks_sample is provided, constructs sample tasks from
        recent dispatch history (_dispatches). Uses compare_policies() to
        evaluate projected energy and returns recommended policy.
        """
        if not tasks_sample:
            if not self._dispatches:
                return {
                    "current_policy": self.policy,
                    "recommended_policy": self.policy,
                    "reason": "no dispatches or sample available; keeping current policy",
                    "sample_size": 0,
                }
            tasks_sample = [
                {
                    "id": d.get("task_id", f"sample_{i}"),
                    "category": d.get("category", "general"),
                    "compute_units": d.get("compute_units", 1),
                }
                for i, d in enumerate(self._dispatches[-50:])
            ]

        matrix = self.compare_policies(tasks_sample, reference_policy=self.policy)
        rec = matrix["recommended_policy"]
        return {
            "current_policy": self.policy,
            "recommended_policy": rec,
            "sample_size": len(tasks_sample),
            "projected_savings_vs_current": matrix["matrix"].get(rec, {}).get("energy_delta_vs_reference", 0.0),
            "comparison_matrix": matrix,
        }

    def auto_tune_policy(
        self,
        tasks_sample: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Apply recommended optimal policy dynamically (v11.17.0)."""
        recommendation = self.recommend_optimal_policy(tasks_sample)
        old_policy = self.policy
        new_policy = recommendation["recommended_policy"]
        self.policy = new_policy
        return {
            "old_policy": old_policy,
            "new_policy": new_policy,
            "changed": old_policy != new_policy,
            "recommendation": recommendation,
        }
