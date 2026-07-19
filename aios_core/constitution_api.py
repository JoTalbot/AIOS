"""
AIOS Constitution API v2.1.1

Interface layer for querying constitutional decisions.
"""

from .constitution_engine import ConstitutionEngine


class ConstitutionAPI:
    def __init__(self):
        self.engine = ConstitutionEngine()

    def check_action(self, action: dict) -> dict:
        return self.engine.evaluate(action)

    def health(self) -> dict:
        return {
            "status": "ONLINE",
            "constitution_version": self.engine.version
        }
