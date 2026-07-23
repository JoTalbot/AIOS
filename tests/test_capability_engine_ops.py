"""Capability engine ops."""
from aios_core.capability_engine import CapabilityEngine
def test_ce(): s = CapabilityEngine().stats(); assert isinstance(s, dict)
