"""AIOS Constitution Validator Layer v2.1.1

Validates actions and decisions against the constitution.
"""


class ConstitutionValidator:
    """Validates constitutional compliance of AIOS operations."""

    def __init__(self):
        self.validations = []
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        """Load constitutional rules."""
        return {
            "autonomy_limited": True,
            "require_goal": True,
            "require_scope": True,
            "require_risk_assessment": True,
            "require_audit_log": True,
            "prohibited_hidden_execution": True,
            "prohibited_uncontrolled_self_modification": True,
        }

    def validate(self, action: dict) -> dict:
        """Validate an action.
        
        Args:
            action: Action to validate
            
        Returns:
            Validation result with status and details
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        if not action.get('goal'):
            validation_result["errors"].append("Missing required field: goal")
            validation_result["valid"] = False
            
        if not action.get('scope'):
            validation_result["errors"].append("Missing required field: scope")
            validation_result["valid"] = False
            
        if not action.get('risk'):
            validation_result["errors"].append("Missing required field: risk")
            validation_result["valid"] = False
            
        if not action.get('audit_log'):
            validation_result["warnings"].append("audit_log not enabled")
        
        self.validations.append(validation_result)
        return validation_result

    def report(self) -> dict:
        """Generate validation report."""
        total = len(self.validations)
        valid = sum(1 for v in self.validations if v["valid"])
        return {
            "total_validations": total,
            "valid": valid,
            "invalid": total - valid,
            "success_rate": valid / total if total > 0 else 0
        }
