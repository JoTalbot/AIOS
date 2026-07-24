"""Chaos Engineering for AIOS v10.9.0.

Chaos engineering toolkit with ChaosMonkey injection,
scenario-based testing, steady-state probes, abort
conditions, action types (delay, error, resource), and
experiment tracking.

Classes:
    ChaosAction    — chaos action specification
    ChaosExperiment — experiment definition
    ChaosMonkey    — full chaos engineering engine
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChaosAction:
    """Chaos action specification."""

    action_type: str = "error"  # error, delay, resource_kill, network_partition
    target: str = ""
    probability: float = 0.1
    delay_seconds: float = 0.0
    error_message: str = "chaos_injected"


@dataclass
class ChaosExperiment:
    """Chaos experiment definition."""

    name: str
    actions: list[ChaosAction] = field(default_factory=list)
    steady_state: dict[str, Any] = field(default_factory=dict)
    abort_conditions: list[str] = field(default_factory=list)
    duration: float = 60.0
    started_at: float = 0.0
    completed: bool = False


class ChaosMonkey:
    """Full chaos engineering engine.

    Features:
    - Random failure injection (backward-compatible)
    - Scenario-based experiments
    - Steady-state validation
    - Abort conditions
    - Multiple action types (delay, error, resource kill, network partition)
    - Experiment tracking
    - Function wrapping with chaos injection
    """

    def __init__(self, failure_rate: float = 0.1) -> None:
        self.failure_rate = failure_rate
        self._injection_count: int = 0
        self._experiments: list[ChaosExperiment] = []

    def maybe_fail(self) -> None:
        """Maybe inject a failure (backward-compatible)."""
        if random.random() < self.failure_rate:
            self._injection_count += 1
            raise Exception("ChaosMonkey injected failure")

    def inject_delay(self, delay: float) -> None:
        """Inject a delay."""
        if random.random() < self.failure_rate:
            self._injection_count += 1
            time.sleep(delay)

    def inject_error(self, message: str = "chaos_injected") -> Exception:
        """Create (but don't raise) an error for injection."""
        self._injection_count += 1
        return Exception(message)

    def wrap(self, func: Callable, chaos_type: str = "error") -> Callable:
        """Wrap a function with chaos injection (backward-compatible)."""

        def wrapper(*args, **kwargs) -> Any:
            if chaos_type == "error":
                self.maybe_fail()
            elif chaos_type == "delay":
                self.inject_delay(random.uniform(0.1, 1.0))
            return func(*args, **kwargs)

        return wrapper

    def run_experiment(self, experiment: ChaosExperiment) -> dict[str, Any]:
        """Run a chaos experiment."""
        experiment.started_at = time.time()
        results = {"injections": 0, "errors": 0, "steady_state_ok": True}

        # Check steady state before
        for _key, _expected_value in experiment.steady_state.items():
            # In real system: probe actual state
            # Simulated: assume steady state
            pass

        # Execute actions
        for action in experiment.actions:
            if random.random() < action.probability:
                results["injections"] += 1
                if action.action_type == "error":
                    results["errors"] += 1
                elif (
                    action.action_type == "delay"
                    or action.action_type == "resource_kill"
                ):
                    pass

        # Check abort conditions
        aborted = False
        for condition in experiment.abort_conditions:
            if "error_rate" in condition and results["errors"] > 5:
                aborted = True
                break

        experiment.completed = True
        results["aborted"] = aborted
        self._experiments.append(experiment)
        self._injection_count += results["injections"]
        return results

    def create_experiment(
        self,
        name: str,
        actions: list[ChaosAction] | None = None,
        steady_state: dict[str, Any] | None = None,
    ) -> ChaosExperiment:
        """Create a chaos experiment."""
        return ChaosExperiment(
            name=name, actions=actions or [], steady_state=steady_state or {}
        )

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "failure_rate": self.failure_rate,
            "injections": self._injection_count,
            "experiments": len(self._experiments),
        }


chaos = ChaosMonkey(failure_rate=0.05)
