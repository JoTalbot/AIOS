class PolicyEngine:
    def __init__(self):
        self.rules = []

    def add_rule(self, rule):
        self.rules.append(rule)

    def check(self, action):
        return all(rule(action) for rule in self.rules)
