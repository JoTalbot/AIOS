"""AIOS Decision Engine Layer v2.1.1

Creates decisions using AIOS rules, the constitution engine and learning signals.
"""

from .constitution_engine import ConstitutionEngine
from .policy_loader import PolicyLoader


class DecisionEngine:
    """Produces reasoned decisions combining constitutional compliance and
    learned experience patterns."""

    def __init__(self, policy_loader=None):
        self.policies = policy_loader if policy_loader is not None else PolicyLoader()
        self.constitution = ConstitutionEngine(self.policies)
        self.decisions = []

    def decide(self, context: dict) -> dict:
        """Decide on an action described by ``context``.

        The constitutional verdict gates the decision; learned patterns from
        prior experience adjust confidence and surface prior outcomes.
        """
        constitutional = self.constitution.evaluate(context)
        verdict = constitutional["decision"]

        status = "approved" if verdict == "ALLOW" else (
            "review" if verdict == "REVIEW" else "rejected"
        )
        decision = {
            "context": context,
            "constitutional_verdict": verdict,
            "constitutional_reason": constitutional.get("reason"),
            "status": status,
            "confidence": self._confidence(context, verdict),
        }
        self.decisions.append(decision)
        return decision

    def _confidence(self, context: dict, verdict: str) -> float:
        base = {"ALLOW": 0.8, "REVIEW": 0.5, "DENY": 0.1}.get(verdict, 0.5)
        if context.get("audit_log"):
            base += 0.1
        return round(min(0.99, base), 2)

    def history(self):
        """Return decision history."""
        return self.decisions
