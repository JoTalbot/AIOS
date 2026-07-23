"""Chaos monkey full."""
from aios_core.chaos import ChaosMonkey
def test(): s=ChaosMonkey().stats(); assert isinstance(s,dict)
