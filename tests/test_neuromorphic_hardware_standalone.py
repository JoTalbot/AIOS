"""neuromorphic_hardware test."""
from aios_core.neuromorphic_hardware import NeuromorphicHardware
def test_init(): s = NeuromorphicHardware().stats(); assert isinstance(s, dict)
