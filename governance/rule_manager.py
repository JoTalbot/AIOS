class RuleManager:
    """AIOS rules management foundation."""

    def __init__(self):
        self.rules = []

    def add(self, rule):
        self.rules.append(rule)

    def list(self):
        return self.rules
