"""Neuromorphic HW full."""
from aios_core.neuromorphic_hardware import NeuromorphicHardware
def test(): s=NeuromorphicHardware().stats(); assert isinstance(s,dict)
