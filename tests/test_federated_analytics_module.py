"""Tests for aios_core/federated_analytics.py"""
from __future__ import annotations
import pytest
from aios_core.federated_analytics import FederatedAnalytics


@pytest.fixture()
def fa():
    return FederatedAnalytics(global_epsilon=1.0)


class TestFederatedAnalytics:
    def test_create(self, fa):
        assert fa is not None

    def test_register_node(self, fa):
        fa.register_node(node_id="node1", epsilon_budget=0.5)

    def test_unregister_node(self, fa):
        fa.register_node(node_id="temp")
        fa.unregister_node("temp")

    def test_get_node(self, fa):
        fa.register_node(node_id="node1")
        node = fa.get_node("node1")
        assert node is not None

    def test_active_nodes(self, fa):
        fa.register_node(node_id="n1")
        fa.register_node(node_id="n2")
        nodes = fa.active_nodes()
        assert isinstance(nodes, list)
        assert len(nodes) >= 2

    def test_pause_resume_node(self, fa):
        fa.register_node(node_id="n1")
        fa.pause_node("n1")
        fa.resume_node("n1")

    def test_consume_budget(self, fa):
        fa.register_node(node_id="n1", epsilon_budget=1.0)
        fa.consume_budget("n1", epsilon=0.1)

    def test_aggregate(self, fa):
        fa.register_node(node_id="n1")
        result = fa.aggregate(local_stats=[{"value": 1.0}, {"value": 2.0}], epsilon=0.1)
        assert result is not None

    def test_check_budget(self, fa):
        fa.register_node(node_id="n1", epsilon_budget=1.0)
        result = fa.check_budget("n1")
        assert result is not None

    def test_stats(self, fa):
        s = fa.stats()
        assert isinstance(s, dict)
