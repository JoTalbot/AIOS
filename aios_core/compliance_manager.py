"""AIOS Compliance Manager"""

class ComplianceManager:
    def __init__(self):
        self.checks = []

    def register(self, check):
        self.checks.append(check)
        return True
