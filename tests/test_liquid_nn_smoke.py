"""liquid_nn smoke test."""
def test_lnn(): from aios_core.liquid_nn import LiquidNeuralNetwork; assert LiquidNeuralNetwork().stats() is not None
