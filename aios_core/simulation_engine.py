"""Simulation Engine for AIOS"""

from typing import Dict, Any, Callable
import random


class SimulationEngine:
    """Runs simulations of AIOS behavior."""

    def __init__(self):
        self.scenarios: Dict[str, Callable] = {}

    def register_scenario(self, name: str, scenario_func: Callable):
        self.scenarios[name] = scenario_func

    def run(self, scenario_name: str, params: Dict = None) -> Dict:
        if scenario_name not in self.scenarios:
            return {"error": "Scenario not found"}
        try:
            result = self.scenarios[scenario_name](params or {})
            return {"scenario": scenario_name, "result": result, "status": "success"}
        except Exception as e:
            return {"scenario": scenario_name, "error": str(e), "status": "failed"}

    def monte_carlo(self, scenario_name: str, runs: int = 100) -> Dict:
        results = []
        for _ in range(runs):
            res = self.run(scenario_name)
            results.append(res.get("result", 0))
        return {
            "runs": runs,
            "average": sum(results) / len(results) if results else 0,
            "min": min(results) if results else 0,
            "max": max(results) if results else 0,
        }

    def stats(self) -> dict:
        return {"scenarios": len(self.scenarios)}
