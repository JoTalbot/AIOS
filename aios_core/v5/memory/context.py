class AgentContext:
    """Runtime context carrying task and memory state."""

    def __init__(self, task=None):
        self.task = task
        self.history = []
        self.memories = []
        self.decisions = []

    def add_memory(self, memory):
        self.memories.append(memory)

    def add_decision(self, decision):
        self.decisions.append(decision)
