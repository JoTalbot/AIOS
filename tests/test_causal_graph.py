"""Tests for causal inference, graph neural networks, and creativity modules."""

from aios_core.causal_inference import CausalInference
from aios_core.graph_neural import GraphNeuralNetwork
from aios_core.creativity import CreativeEngine


def test_causal_inference_stats():
    ci = CausalInference()
    s = ci.stats()
    assert isinstance(s, dict)


def test_graph_neural_network_stats():
    gnn = GraphNeuralNetwork()
    s = gnn.stats()
    assert isinstance(s, dict)


def test_creative_engine_stats():
    ce = CreativeEngine()
    s = ce.stats()
    assert isinstance(s, dict)
