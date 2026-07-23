"""chaos_testing test."""
from aios_core.chaos_testing import ChaosTester
def test_init(): s = ChaosTester().stats(); assert isinstance(s, dict)
