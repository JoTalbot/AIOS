"""chaos_testing test."""
def test(): from aios_core.chaos_testing import ChaosTester; s = ChaosTester().stats(); assert isinstance(s, dict)
