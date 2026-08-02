class FeedbackLoop:
    """Learning feedback cycle foundation."""

    def __init__(self):
        self.feedback = []

    def add(self, result):
        self.feedback.append(result)

    def get(self):
        return self.feedback
