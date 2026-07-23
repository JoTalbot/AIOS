"""Test AGI safety."""
from aios_core.agi_safety import AGISafety
def test_agi(): assert AGISafety().stats() is not None
