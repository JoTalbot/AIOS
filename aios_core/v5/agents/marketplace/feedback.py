class FeedbackLoop:
    """Agent learning feedback foundation."""

    def __init__(self, memory=None):
        self.memory = memory

    def record(self, result):
        if self.memory:
            self.memory.remember(result)
        return {
            "recorded": True,
            "result": result
        }
