"""Test AI safety amplification."""
from aios_core.ai_safety_amplification import IteratedAmplification
def test_amplification(): assert IteratedAmplification().stats() is not None
