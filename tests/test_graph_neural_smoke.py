"""graph_neural smoke test."""
def test_gnn(): from aios_core.graph_neural import GraphNeuralNetwork; assert GraphNeuralNetwork().stats() is not None
