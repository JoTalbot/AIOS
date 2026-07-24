"""Simulation Engine for AIOS v10.10.0.

Simulation engine: scenario registration and execution,
Monte Carlo simulation, parameter sweeps, batch execution,
result aggregation, confidence intervals, and dependency
management.

Classes:
    SimulationScenario — registered scenario descriptor
    SimulationEngine   — full simulation engine
"""

from __future__ import annotations

import logging
import math
import random
import statistics
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SimulationScenario:
    """Registered scenario descriptor."""

    def __init__(self, name: str, func: Callable, params_schema: dict[str, Any] | None = None) -> None:
        self.name = name
        self.func = func
        self.params_schema = params_schema or {}
        self.runs: int = 0
        self._last_result: Any = None

    def execute(self, params: dict[str, Any]) -> Any:
        """Execute the scenario."""
        self.runs += 1
        result = self.func(params)
        self._last_result = result
        return result

    def stats(self) -> dict[str, Any]:
        return {"name": self.name, "runs": self.runs}


class SimulationEngine:
    """Runs simulations of AIOS behavior."""

    def __init__(self) -> None:
        self.scenarios: dict[str, SimulationScenario] = {}
        self._results_log: list[dict[str, Any]] = []
        self._dependencies: dict[str, list[str]] = {}  # scenario → depends_on

    def register_scenario(self, name: str, scenario_func: Callable, params_schema: dict[str, Any] | None = None) -> None:
        """Register a scenario (backward-compatible)."""
        self.scenarios[name] = SimulationScenario(name, scenario_func, params_schema)

    def add_dependency(self, scenario: str, depends_on: str) -> None:
        """Add execution dependency between scenarios."""
        if scenario not in self._dependencies:
            self._dependencies[scenario] = []
        self._dependencies[scenario].append(depends_on)

    def run(self, scenario_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a single scenario (backward-compatible)."""
        if scenario_name not in self.scenarios:
            return {"error": "Scenario not found"}
        # Execute dependencies first
        deps = self._dependencies.get(scenario_name, [])
        for dep in deps:
            self.run(dep, params)
        try:
            scenario = self.scenarios[scenario_name]
            result = scenario.execute(params or {})
            output = {"scenario": scenario_name, "result": result, "status": "success"}
            self._results_log.append(output)
            return output
        except Exception as e:
            output = {"scenario": scenario_name, "error": str(e), "status": "failed"}
            self._results_log.append(output)
            return output

    def monte_carlo(self, scenario_name: str, runs: int = 100, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Monte Carlo simulation (backward-compatible + enhanced)."""
        results: list[Any] = []
        for _ in range(runs):
            res = self.run(scenario_name, params)
            if res.get("status") == "success":
                results.append(res.get("result", 0))
        if not results:
            return {"runs": runs, "average": 0, "min": 0, "max": 0}
        avg = sum(results) / len(results) if isinstance(results[0], (int, float)) else None
        nums = results if all(isinstance(r, (int, float)) for r in results) else []
        output: dict[str, Any] = {
            "runs": runs,
            "successful": len(results),
            "average": round(avg, 4) if avg is not None else None,
            "min": min(nums) if nums else None,
            "max": max(nums) if nums else None,
        }
        # Confidence interval (95%)
        if nums and len(nums) > 2:
            std = statistics.stdev(nums)
            ci_half = 1.96 * std / math.sqrt(len(nums))
            output["confidence_interval"] = (round(avg - ci_half, 4), round(avg + ci_half, 4))
            output["std"] = round(std, 4)
        return output

    def parameter_sweep(self, scenario_name: str, param_name: str, values: list[Any], base_params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Sweep a parameter across multiple values."""
        results: list[dict[str, Any]] = []
        for value in values:
            params = dict(base_params or {})
            params[param_name] = value
            result = self.run(scenario_name, params)
            result["sweep_value"] = value
            results.append(result)
        return results

    def batch_execute(self, scenario_names: list[str], params: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
        """Execute multiple scenarios in batch."""
        results: dict[str, dict[str, Any]] = {}
        for name in scenario_names:
            results[name] = self.run(name, params)
        return results

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "scenarios": len(self.scenarios),
            "total_runs": sum(s.runs for s in self.scenarios.values()),
            "results_logged": len(self._results_log),
        }
