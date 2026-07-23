"""Test safety scientist."""
from aios_core.ai_safety_scientist import AISafetyScientist
def test_scientist(): assert AISafetyScientist().stats() is not None
