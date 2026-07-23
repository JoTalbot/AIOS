"""nas test."""
def test(): from aios_core.nas import NeuralArchitectureSearch; s = NeuralArchitectureSearch().stats(); assert isinstance(s, dict)
