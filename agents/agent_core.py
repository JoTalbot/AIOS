class AgentCore:
    """AIOS agent core foundation."""

    def __init__(self, name):
        self.name = name

    def execute(self, task):
        return {
            "agent": self.name,
            "task": task,
            "executed": True
        }
