from dataclasses import dataclass

@dataclass
class AccessRule:
    capability: str
    scope: str
    allowed: bool = True


class AccessControlMatrix:
    def __init__(self):
        self.rules = []

    def add_rule(self, rule: AccessRule):
        self.rules.append(rule)

    def check(self, capability: str, scope: str) -> bool:
        for rule in self.rules:
            if rule.capability == capability and rule.scope == scope:
                return rule.allowed
        return False
