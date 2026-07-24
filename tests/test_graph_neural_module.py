"""Tests for aios_core/graph_neural.py"""
from __future__ import annotations
import pytest
from aios_core.graph_neural import GraphNeuralNetwork


@pytest.fixture()
def gnn():
    return GraphNeuralNetwork(layers=2, hidden_dim=16)


class TestGraphNeuralNetwork:
    def test_create(self, gnn):
        assert gnn is not None

    def test_add_node(self, gnn):
        gnn.add_node(node_id="n1", features=[1.0, 0.5, 0.3])

    def test_add_edge(self, gnn):
        gnn.add_node(node_id="n1", features=[1.0])
        gnn.add_node(node_id="n2", features=[0.5])
        gnn.add_edge(src="n1", dst="n2")

    def test_get_node(self, gnn):
        gnn.add_node(node_id="n1", features=[1.0])
        node = gnn.get_node("n1")
        assert node is not None

    def test_get_neighbors(self, gnn):
        gnn.add_node(node_id="n1", features=[1.0])
        gnn.add_node(node_id="n2", features=[0.5])
        gnn.add_edge(src="n1", dst="n2")
        neighbors = gnn.get_neighbors("n1")
        assert isinstance(neighbors, list)

    def test_remove_node(self, gnn):
        gnn.add_node(node_id="n1", features=[1.0])
        gnn.remove_node("n1")

    def test_message_passing(self, gnn):
        gnn.add_node(node_id="n1", features=[1.0, 0.5])
        gnn.add_node(node_id="n2", features=[0.3, 0.8])
        gnn.add_edge(src="n1", dst="n2")
        result = gnn.message_passing()
        assert isinstance(result, dict)

    def test_classify_node(self, gnn):
        gnn.add_node(node_id="n1", features=[1.0, 0.5], label="A")
        gnn.add_node(node_id="n2", features=[0.3, 0.8], label="B")
        gnn.add_edge(src="n1", dst="n2")
        gnn.message_passing()
        result = gnn.classify_node("n1")
        assert result is not None

    def test_stats(self, gnn):
        s = gnn.stats()
        assert isinstance(s, dict)
