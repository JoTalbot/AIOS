"""Test long term safety."""
from aios_core.ai_safety_long_term import LongTermSafety
def test_longterm(): assert LongTermSafety().stats() is not None
