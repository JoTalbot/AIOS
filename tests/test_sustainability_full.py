"""Sustainability full."""
from aios_core.sustainability import SustainabilityTracker
def test(): s=SustainabilityTracker().stats(); assert isinstance(s,dict)
