"""capability_engine test."""
def test(): from aios_core.capability_engine import CapabilityEngine; s = CapabilityEngine().stats(); assert isinstance(s, dict)
