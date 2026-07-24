"""Chaos Testing Framework for AIOS v10.5.0.

Inject failures and latency for resilience testing with scenarios,
steady-state validation, probes, abort conditions, and history tracking.

Classes:
    ChaosAction     — failure injection type (network, latency, error, CPU)
    ChaosScenario   — named scenario with actions, probes, abort conditions
    ChaosResult     — scenario execution result
    ChaosTester     — enhanced chaos framework with scenarios and validation
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class ChaosAction(str, Enum):
    """Chaos injection types."""
    NETWORK_PARTITION = "network_partition"
    LATENCY_INJECTION = "latency_injection"
    ERROR_INJECTION = "error_injection"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    SERVICE_KILL = "service_kill"


# ── Chaos Scenario ───────────────────────────────────────────────────────────

@dataclass
class ChaosScenario:
    """Named chaos scenario with actions, probes, abort conditions."""
    name: str
    actions: list[ChaosAction] = field(default_factory=list)
    duration: float = 60.0  # seconds
    target: str = ""  # which service/system to target
    probe_fn: Optional[Callable[[], bool]] = None  # steady-state check
    abort_fn: Optional[Callable[[], bool]] = None  # abort condition
    probability: float = 1.0  # injection probability (0..1)
    latency_ms: int = 100
    error_message: str = "chaos_injected_error"
    tags: list[str] = field(default_factory=list)


# ── Chaos Result ─────────────────────────────────────────────────────────────

@dataclass
class ChaosResult:
    """Result of a chaos scenario execution."""
    scenario_name: str
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    actions_executed: list[str] = field(default_factory=list)
    probe_results: list[bool] = field(default_factory=list)
    aborted: bool = False
    steady_state_maintained: bool = True

    def duration(self) -> float:
        """Return scenario duration."""
        if self.finished_at and self.started_at:
            return self.finished_at - self.started_at
        return 0.0


# ── Chaos Tester ─────────────────────────────────────────────────────────────

class ChaosTester:
    """Enhanced chaos testing framework with scenarios and validation.

    Features:
    - Scenario-based chaos (not just random injection)
    - Steady-state validation (probe before and after)
    - Abort conditions (stop if system is unrecoverable)
    - History tracking (all scenario results)
    - Per-action configuration (probability, latency, error message)
    """

    def __init__(self, failure_probability: float = 0.1, latency_ms: int = 0) -> None:
        """Initialize ChaosTester."""
        self.failure_probability = failure_probability
        self.latency_ms = latency_ms
        self.scenarios: dict[str, ChaosScenario] = {}
        self.history: list[ChaosResult] = []
        self._active_actions: dict[str, bool] = {}  # action → currently active

    # ── Scenario Registration ────────────────────────────────────

    def register_scenario(self, scenario: ChaosScenario) -> None:
        """Register a chaos scenario."""
        self.scenarios[scenario.name] = scenario

    def remove_scenario(self, name: str) -> None:
        """Remove a scenario."""
        del self.scenarios[name]

    # ── Scenario Execution ───────────────────────────────────────

    def run_scenario(self, name: str) -> ChaosResult:
        """Execute a chaos scenario with steady-state validation.

        Steps:
        1. Run probe (steady-state check) BEFORE injection
        2. Inject chaos actions
        3. Run probe AFTER injection
        4. Check abort conditions
        5. Record result
        """
        scenario = self.scenarios.get(name)
        if scenario is None:
            raise KeyError(f"Scenario '{name}' not found")

        result = ChaosResult(scenario_name=name)

        # ── Pre-injection probe ──
        if scenario.probe_fn:
            result.probe_results.append(scenario.probe_fn())

        # ── Inject actions ──
        for action in scenario.actions:
            if random.random() < scenario.probability:
                self._inject_action(action, scenario)
                result.actions_executed.append(action.value)
                self._active_actions[action.value] = True

            # Check abort condition during execution
            if scenario.abort_fn and scenario.abort_fn():
                result.aborted = True
                logger.warning("Scenario '%s' aborted", name)
                break

        # ── Post-injection probe ──
        if scenario.probe_fn:
            result.probe_results.append(scenario.probe_fn())

        # ── Determine steady state ──
        if result.probe_results:
            result.steady_state_maintained = all(result.probe_results)

        # ── Clean up active actions ──
        for action in scenario.actions:
            self._active_actions.pop(action.value, None)

        result.finished_at = time.time()
        self.history.append(result)
        return result

    def _inject_action(self, action: ChaosAction, scenario: ChaosScenario) -> None:
        """Execute a single chaos action."""
        if action == ChaosAction.LATENCY_INJECTION:
            logger.info("Injecting %dms latency on '%s'", scenario.latency_ms, scenario.target)
        elif action == ChaosAction.ERROR_INJECTION:
            logger.info("Injecting error '%s' on '%s'", scenario.error_message, scenario.target)
        elif action == ChaosAction.NETWORK_PARTITION:
            logger.info("Injecting network partition on '%s'", scenario.target)
        elif action == ChaosAction.CPU_STRESS:
            logger.info("Injecting CPU stress on '%s'", scenario.target)
        elif action == ChaosAction.MEMORY_STRESS:
            logger.info("Injecting memory stress on '%s'", scenario.target)
        elif action == ChaosAction.SERVICE_KILL:
            logger.info("Simulating service kill on '%s'", scenario.target)

    # ── Simple Injection (backward-compatible) ──────────────────

    def inject(self, func: Callable) -> Callable:
        """Wrap a function with chaos injection (backward-compatible decorator)."""
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if random.random() < self.failure_probability:
                raise Exception("Chaos injection: simulated failure")
            if self.latency_ms > 0:
                time.sleep(self.latency_ms / 1000)
            return func(*args, **kwargs)
        return wrapper

    # ── Active Actions ──────────────────────────────────────────

    def is_action_active(self, action: str) -> bool:
        """Check if a chaos action is currently active."""
        return self._active_actions.get(action, False)

    def clear_active_actions(self) -> None:
        """Clear all active chaos actions."""
        self._active_actions.clear()

    # ── History ──────────────────────────────────────────────────

    def get_history(self, limit: int = 50) -> list[ChaosResult]:
        """Return recent scenario results."""
        return self.history[-limit:]

    def get_scenario_results(self, name: str) -> list[ChaosResult]:
        """Return all results for a specific scenario."""
        return [r for r in self.history if r.scenario_name == name]

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        total = len(self.history)
        aborted = sum(1 for r in self.history if r.aborted)
        maintained = sum(1 for r in self.history if r.steady_state_maintained)
        return {
            "failure_probability": self.failure_probability,
            "latency_ms": self.latency_ms,
            "scenarios": len(self.scenarios),
            "history_size": total,
            "aborted_count": aborted,
            "steady_state_maintained": maintained,
            "steady_state_rate": maintained / total if total > 0 else 0.0,
        }
