"""spiking_nn smoke test."""
def test_snn(): from aios_core.spiking_nn import SpikingNeuralNetwork; assert SpikingNeuralNetwork().stats() is not None
