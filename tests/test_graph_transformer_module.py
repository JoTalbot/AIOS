"""Tests for aios_core/graph_transformer.py"""
from __future__ import annotations
import pytest
from aios_core.graph_transformer import GraphTransformer


@pytest.fixture()
def gt():
    return GraphTransformer(dim=16, heads=2, layers=2)


class TestGraphTransformer:
    def test_create(self, gt):
        assert gt is not None

    def test_add_node(self, gt):
        gt.add_node(node_id="n1")

    def test_add_node_with_embedding(self, gt):
        gt.add_node(node_id="n1", embedding=[0.1] * 16)

    def test_add_edge(self, gt):
        gt.add_node(node_id="n1")
        gt.add_node(node_id="n2")
        gt.add_edge(src="n1", dst="n2")

    def test_get_neighbors(self, gt):
        gt.add_node(node_id="n1")
        gt.add_node(node_id="n2")
        gt.add_edge(src="n1", dst="n2")
        neighbors = gt.get_neighbors("n1")
        assert isinstance(neighbors, list)

    def test_forward(self, gt):
        gt.add_node(node_id="n1", embedding=[0.1] * 16)
        gt.add_node(node_id="n2", embedding=[0.2] * 16)
        gt.add_edge(src="n1", dst="n2")
        result = gt.forward()
        assert result is not None

    def test_readout(self, gt):
        gt.add_node(node_id="n1", embedding=[0.1] * 16)
        result = gt.readout()
        assert result is not None

    def test_stats(self, gt):
        s = gt.stats()
        assert isinstance(s, dict)
