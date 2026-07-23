from aios_core.neuromorphic_matrix import NeuromorphicMatrix
from aios_core.neuromorphic_hardware import NeuromorphicHardware
def test(): assert NeuromorphicMatrix().stats() is not None; assert NeuromorphicHardware().stats() is not None
