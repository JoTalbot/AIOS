"""AIOS Decision Auditor"""

class DecisionAuditor:
    def __init__(self):
        self.records = []

    def audit(self, decision):
        self.records.append(decision)
        return True
