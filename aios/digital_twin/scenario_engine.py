class ScenarioEngine:
    def __init__(self):
        self.scenarios = []

    def create(self, name, changes):
        scenario = {"name": name, "changes": changes}
        self.scenarios.append(scenario)
        return scenario

    def list(self):
        return self.scenarios
