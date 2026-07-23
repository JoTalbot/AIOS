"""Spiking NN full ops."""
from aios_core.spiking_nn import SpikingNeuralNetwork
def test_snn(): s=SpikingNeuralNetwork().stats(); assert isinstance(s,dict)
