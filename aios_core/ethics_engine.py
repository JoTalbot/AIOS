"""AIOS Ethics Engine"""

class EthicsEngine:
    def __init__(self):
        self.rules = []

    def add_rule(self, rule):
        self.rules.append(rule)

    def evaluate(self, action):
        return True
