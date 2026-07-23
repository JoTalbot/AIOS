"""Liquid NN full."""
from aios_core.liquid_nn import LiquidNeuralNetwork
def test(): s=LiquidNeuralNetwork().stats(); assert isinstance(s,dict)
