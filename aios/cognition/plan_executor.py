class PlanExecutor:
    """Executes cognitive plans through an execution callback."""

    def __init__(self, executor=None):
        self.executor = executor

    def execute(self, plan):
        if self.executor:
            return self.executor(plan)
        return plan
