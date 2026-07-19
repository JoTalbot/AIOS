"""AIOS Constitution Engine Layer v2.1.1

Core constitutional decision-making engine.
"""

from .policy_loader import PolicyLoader

class ConstitutionEngine:
    """Evaluates actions against AIOS constitutional principles."""

    def __init__(self, policy_loader=None):
        self.decisions = []
        self.version = "2.1.1"
        self.policies = policy_loader if policy_loader is not None else PolicyLoader()
        # Required fields may be extended by policy in the future; defaults below.
        self.required_fields = ['goal', 'scope', 'risk', 'audit_log']

    def evaluate(self, action: dict) -> dict:
        """Evaluate an action against constitutional rules.
        
        Args:
            action: Action request with goal, scope, risk, audit_log
            
        Returns:
            Decision with ALLOW/REVIEW/DENY status
        """
        # Validate required fields
        required_fields = self.required_fields
        if not all(field in action for field in required_fields):
            return {
                "decision": "DENY",
                "reason": "missing_required_fields",
                "required_fields": required_fields,
                "constitution_version": self.version
            }
        
        # Evaluate constitutional compliance
        decision_result = self._evaluate_constitution(action)
        self.decisions.append(decision_result)
        return decision_result

    def _evaluate_constitution(self, action: dict) -> dict:
        """Apply constitutional rules to action."""
        # Check autonomy principles
        if not self._check_autonomy(action):
            return {
                "decision": "DENY",
                "reason": "autonomy_violation",
                "constitution_version": self.version,
                "details": "Action violates autonomy constraints"
            }
        
        # Check safety principles
        if not self._check_safety(action):
            return {
                "decision": "REVIEW",
                "reason": "safety_review_required",
                "constitution_version": self.version,
                "details": "Safety constraints require review"
            }
        
        return {
            "decision": "ALLOW",
            "reason": "constitutional_compliance",
            "constitution_version": self.version,
            "details": "Action complies with constitutional principles"
        }

    def _check_autonomy(self, action: dict) -> bool:
        """Check autonomy constraints."""
        return (
            action.get('goal') is not None and
            action.get('scope') is not None and
            action.get('risk') is not None
        )

    def _check_safety(self, action: dict) -> bool:
        """Check safety constraints."""
        risk_level = action.get('risk', 'high')
        # Risk levels are driven by the security policy threat model.
        allowed_risks = self.policies.safety_threat_levels.keys() or ['low', 'medium', 'high']
        return risk_level in allowed_risks

    def history(self) -> list:
        """Return decision history."""
        return self.decisions
