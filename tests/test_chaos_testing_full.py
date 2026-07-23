"""Chaos testing full."""
from aios_core.chaos_testing import ChaosTester
def test(): s=ChaosTester().stats(); assert isinstance(s,dict)
