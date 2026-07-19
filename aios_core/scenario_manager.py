"""
AIOS Scenario Manager Layer v2.1.1

Manages simulation and testing scenarios.
"""


class ScenarioManager:
    def __init__(self):
        self.scenarios = []

    def add(self, scenario: dict):
        self.scenarios.append(scenario)
        return scenario

    def list_scenarios(self):
        return self.scenarios
