"""Test safety evaluations."""
from aios_core.ai_safety_evals import SafetyEvaluator
def test_evals(): assert SafetyEvaluator().stats() is not None
