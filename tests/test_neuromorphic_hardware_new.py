"""neuromorphic_hardware test."""
def test(): from aios_core.neuromorphic_hardware import NeuromorphicHardware; s = NeuromorphicHardware().stats(); assert isinstance(s, dict)
