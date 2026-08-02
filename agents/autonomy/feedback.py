class FeedbackLoop:
    """Learning feedback loop foundation."""

    def __init__(self):
        self.history = []

    def record(self, result):
        self.history.append(result)

    def review(self):
        return self.history
