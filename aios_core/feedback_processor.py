"""
AIOS Feedback Processor Layer v2.1.1

Processes feedback from nodes and improves future decisions.
"""


class FeedbackProcessor:
    def __init__(self):
        self.feedback = []

    def process(self, item: dict):
        self.feedback.append(item)
        return item

    def history(self):
        return self.feedback
