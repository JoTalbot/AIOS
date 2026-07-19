"""
AIOS Integrity Checker Layer v2.1.1

Verifies integrity of AIOS components and detects unexpected changes.
"""


class IntegrityChecker:
    def __init__(self):
        self.checks = []

    def verify(self, component: str, expected_hash: str, actual_hash: str):
        result = {
            "component": component,
            "valid": expected_hash == actual_hash,
            "expected": expected_hash,
            "actual": actual_hash,
        }
        self.checks.append(result)
        return result

    def report(self):
        return self.checks
