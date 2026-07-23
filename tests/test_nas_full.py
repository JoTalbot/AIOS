"""NAS full ops."""
from aios_core.nas import NeuralArchitectureSearch
def test(): s=NeuralArchitectureSearch().stats(); assert isinstance(s,dict)
