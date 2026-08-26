from dataclasses import dataclass


@dataclass
class LearningEvent:
    agent: str
    knowledge: dict
    score: float


class CrossAgentLearning:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)

    def best_patterns(self):
        return sorted(self.events, key=lambda x: x.score, reverse=True)
