class PolicyEngine:
    def __init__(self):
        self.rules = {}

    def allow(self, action: str, subject: str) -> bool:
        return self.rules.get((subject, action), False)

    def set_rule(self, subject: str, action: str, allowed: bool = True):
        self.rules[(subject, action)] = allowed
