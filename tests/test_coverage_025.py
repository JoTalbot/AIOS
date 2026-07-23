"""Test neuromorphic hardware."""
from aios_core.neuromorphic_hardware import NeuromorphicHardware
from aios_core.neuromorphic_matrix import NeuromorphicMatrix
def test_hw(): assert NeuromorphicHardware().stats() is not None
def test_matrix(): assert NeuromorphicMatrix().stats() is not None
