from dataclasses import dataclass


@dataclass
class PolicyRule:

    name: str
    enabled: bool = True


class PolicyEnforcementEngine:

    def __init__(self):
        self.rules = {}

    def add_rule(self, rule):
        self.rules[rule.name] = rule

    def check(self, action):
        for rule in self.rules.values():
            if rule.enabled and rule.name == action:
                return True
        return False
