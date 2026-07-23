"""test_nas_scenario test."""
from aios_core.nas import NeuralArchitectureSearch

def test_nas():
    s = NeuralArchitectureSearch().stats()
    assert isinstance(s, dict)

