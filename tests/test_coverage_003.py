"""Test safety deception detection."""
from aios_core.ai_safety_deception import DeceptionDetector
def test_deception(): assert DeceptionDetector().stats() is not None
