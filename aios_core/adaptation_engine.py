"""AIOS Adaptation Engine"""

class AdaptationEngine:
    def __init__(self):
        self.state = {}

    def adapt(self, key, value):
        self.state[key] = value
        return self.state
