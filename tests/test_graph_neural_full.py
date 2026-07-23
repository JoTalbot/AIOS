"""Graph neural full ops."""
from aios_core.graph_neural import GraphNeuralNetwork
def test_gnn(): s=GraphNeuralNetwork().stats(); assert isinstance(s,dict)
