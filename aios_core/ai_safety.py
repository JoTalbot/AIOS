"""Comprehensive AI Safety Framework for AIOS"""

import time
from typing import Any, Dict, List, Optional

__all__ = [
    "AISafetyFramework",
    "AlignmentSafety",
    "ConstitutionalSafety",
    "GovernanceSafety",
    "InterpretabilitySafety",
    "RobustnessSafety",
    "BiasSafety",
    "PrivacySafety",
    "AdversarialSafety",
    "ResourceSafety"
]


class SafetyLayer:
    """Base class for all safety layers."""
    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement check method.")


class ConstitutionalSafety(SafetyLayer):
    """Safety layer checking for constitutional violations (e.g. harm language)."""

    def __init__(self):
        self.harm_keywords = ["harm", "damage", "injure", "destroy", "kill", "attack", "abuse"]
        self.discrimination_keywords = ["discriminate", "racist", "sexist", "bias"]

    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        action_str = str(action).lower()
        violations = []
        
        if any(word in action_str for word in self.harm_keywords):
            violations.append("non_maleficence")
        if any(word in action_str for word in self.discrimination_keywords):
            violations.append("fairness_and_equity")
            
        score = 1.0
        if violations:
            score -= 0.5 * len(violations)
            
        return {
            "safe": len(violations) == 0,
            "score": max(0.0, score),
            "violations": violations,
            "details": f"Checked against {len(self.harm_keywords) + len(self.discrimination_keywords)} constitutional rules."
        }


class AlignmentSafety(SafetyLayer):
    """Safety layer quantifying value-alignment of actions."""

    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Simulate alignment checking against system values
        intent = action.get("intent", "").lower()
        if "override" in intent or "bypass" in intent:
            return {"safe": False, "score": 0.4, "alignment_score": 0.3, "reason": "Bypass intent detected"}
        return {"safe": True, "score": 0.95, "alignment_score": 0.92}


class InterpretabilitySafety(SafetyLayer):
    """Safety layer assessing how interpretable an action is."""

    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        complexity = action.get("complexity", 1.0)
        # If action is too complex, it's less interpretable
        if complexity > 8.0:
            return {"safe": False, "score": 0.5, "interpretability": 0.4, "reason": "Action too complex to interpret"}
        return {"safe": True, "score": 0.88, "interpretability": 0.85}


class RobustnessSafety(SafetyLayer):
    """Safety layer checking robustness against perturbations."""

    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # A simple heuristic for robustness
        params = action.get("parameters", {})
        if not params:
            return {"safe": True, "score": 0.90, "robustness": 0.88}
        
        # Check if parameters have bounds
        has_bounds = any(isinstance(v, dict) and ("min" in v or "max" in v) for v in params.values())
        if not has_bounds and len(params) > 5:
            return {"safe": False, "score": 0.6, "robustness": 0.5, "reason": "Many unbounded parameters"}
            
        return {"safe": True, "score": 0.90, "robustness": 0.88}


class GovernanceSafety(SafetyLayer):
    """Safety layer enforcing governance compliance."""

    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        policy = action.get("policy", "")
        if policy == "unrestricted":
            return {"safe": False, "score": 0.2, "governance_compliance": 0.1, "reason": "Unrestricted policy not allowed"}
        return {"safe": True, "score": 0.93, "governance_compliance": 0.91}


class BiasSafety(SafetyLayer):
    """Safety layer evaluating statistical bias potential."""
    
    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        target_demographics = action.get("demographics", [])
        if len(target_demographics) == 1:
            return {"safe": False, "score": 0.4, "bias_risk": 0.8, "reason": "Action targets a single demographic exclusively"}
        return {"safe": True, "score": 0.98, "bias_risk": 0.05}


class PrivacySafety(SafetyLayer):
    """Safety layer protecting PII and sensitive data."""
    
    def __init__(self):
        self.pii_fields = ["ssn", "social_security", "credit_card", "password", "health_record"]

    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data_fields = action.get("data_fields", [])
        exposed = [f for f in data_fields if f.lower() in self.pii_fields]
        if exposed:
            return {"safe": False, "score": 0.0, "privacy_risk": 1.0, "exposed_fields": exposed}
        return {"safe": True, "score": 1.0, "privacy_risk": 0.0}


class AdversarialSafety(SafetyLayer):
    """Safety layer detecting adversarial inputs (e.g. prompt injection)."""
    
    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = str(action.get("payload", "")).lower()
        if "ignore previous instructions" in payload or "system prompt" in payload:
            return {"safe": False, "score": 0.1, "adversarial_risk": 0.9, "reason": "Prompt injection detected"}
        return {"safe": True, "score": 0.99, "adversarial_risk": 0.01}


class ResourceSafety(SafetyLayer):
    """Safety layer ensuring an action does not cause resource exhaustion."""
    
    def check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        compute_req = action.get("compute_required", 0)
        memory_req = action.get("memory_required_gb", 0)
        
        if compute_req > 1000 or memory_req > 128:
            return {"safe": False, "score": 0.3, "reason": "Resource requirements exceed limits"}
        return {"safe": True, "score": 0.96}


class AISafetyFramework:
    """State-of-the-art AI safety framework with multiple layers of protection."""

    def __init__(self):
        """Initialize AISafetyFramework."""
        self.safety_layers: Dict[str, SafetyLayer] = {
            "constitutional": ConstitutionalSafety(),
            "alignment": AlignmentSafety(),
            "interpretability": InterpretabilitySafety(),
            "robustness": RobustnessSafety(),
            "governance": GovernanceSafety(),
            "bias": BiasSafety(),
            "privacy": PrivacySafety(),
            "adversarial": AdversarialSafety(),
            "resource": ResourceSafety()
        }
        self.incidents: List[Dict[str, Any]] = []
        self.safety_checks_performed = 0
        self.global_threshold = 0.7

    def add_custom_layer(self, name: str, layer: SafetyLayer):
        """Allow dynamic addition of custom safety layers."""
        self.safety_layers[name] = layer

    def comprehensive_safety_check(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run all safety layers on an action."""
        self.safety_checks_performed += 1
        results = {}
        action_id = action.get("id", f"action_{self.safety_checks_performed}")

        for layer_name, layer in self.safety_layers.items():
            result = layer.check(action, context)
            results[layer_name] = result

            if not result.get("safe", True):
                self.incidents.append(
                    {
                        "action_id": action_id,
                        "action": action, 
                        "layer": layer_name, 
                        "details": result,
                        "timestamp": time.time()
                    }
                )

        overall_safe = all(r.get("safe", True) for r in results.values())
        avg_score = sum(r.get("score", 1.0) for r in results.values()) / len(results)
        
        # Enforce global threshold
        if avg_score < self.global_threshold:
            overall_safe = False

        return {
            "overall_safe": overall_safe,
            "average_safety_score": round(avg_score, 3),
            "layer_results": results,
            "incidents_this_check": len([r for r in results.values() if not r.get("safe", True)]),
            "timestamp": time.time()
        }

    def get_safety_report(self) -> Dict[str, Any]:
        """Execute get safety report."""
        return {
            "total_checks": self.safety_checks_performed,
            "total_incidents": len(self.incidents),
            "layers_active": list(self.safety_layers.keys()),
            "recent_incidents": self.incidents[-5:] if self.incidents else [],
            "system_health": "Critical" if len(self.incidents) > 10 else "Nominal"
        }

    def stats(self) -> Dict[str, Any]:
        """Return statistics dict."""
        return {
            "layers": len(self.safety_layers),
            "checks_performed": self.safety_checks_performed,
            "incidents": len(self.incidents),
            "global_threshold": self.global_threshold
        }

    def clear_incidents(self):
        """Clear incident history for testing or administrative resets."""
        self.incidents.clear()
