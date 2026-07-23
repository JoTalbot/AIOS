"""test_neural_ode_scenario test."""
from aios_core.neural_ode import NeuralODE

def test_ode():
    s = NeuralODE().stats()
    assert isinstance(s, dict)

