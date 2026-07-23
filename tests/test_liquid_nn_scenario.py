"""test_liquid_nn_scenario test."""
from aios_core.liquid_nn import LiquidNeuralNetwork

def test_liquid():
    s = LiquidNeuralNetwork().stats()
    assert isinstance(s, dict)

