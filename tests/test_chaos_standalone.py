"""chaos test."""
from aios_core.chaos import ChaosMonkey
def test_init(): s = ChaosMonkey().stats(); assert isinstance(s, dict)
