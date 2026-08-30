class AgentBudget:
    def __init__(self, max_actions=100, max_runtime=3600):
        self.max_actions = max_actions
        self.max_runtime = max_runtime
        self.actions_used = 0

    def can_execute(self):
        return self.actions_used < self.max_actions

    def consume(self):
        self.actions_used += 1
