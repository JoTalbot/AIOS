"""Test safety interpretability."""
from aios_core.ai_safety_interpretability import SafetyInterpretability
def test_interpret(): assert SafetyInterpretability().stats() is not None
