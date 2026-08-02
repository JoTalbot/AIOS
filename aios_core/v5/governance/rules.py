class RuleSet:
    def __init__(self):
        self.rules = []

    def add(self, rule: str):
        self.rules.append(rule)

    def all(self):
        return self.rules
