"""
AIOS Agent Test Runner v2.1.1

Runs agent actions through simulation and constitutional validation.
"""

from simulation_engine import SimulationEngine


class AgentTestRunner:
    def __init__(self):
        self.simulator = SimulationEngine()

    def run(self, actions: list) -> list:
        return [self.simulator.simulate(action) for action in actions]


if __name__ == "__main__":
    runner = AgentTestRunner()

    tests = [
        {
            "goal": "system_check",
            "scope": "local_node",
            "risk": "low",
            "reversible": True,
            "audit_log": True
        }
    ]

    print(runner.run(tests))
