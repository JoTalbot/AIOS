class FeedbackCollector:
    """AIOS feedback collection foundation."""

    def __init__(self):
        self.feedback = []

    def collect(self, result):
        self.feedback.append(result)

    def all(self):
        return self.feedback
