"""chaos test."""
def test(): from aios_core.chaos import ChaosMonkey; s = ChaosMonkey().stats(); assert isinstance(s, dict)
