class CognitiveLoop:
    """Minimal observe-plan-execute-evaluate loop."""

    def __init__(self, planner=None, executor=None):
        self.planner = planner
        self.executor = executor

    def run(self, observation):
        plan = self.planner.plan(observation) if self.planner else observation
        return self.executor.execute(plan) if self.executor else plan
