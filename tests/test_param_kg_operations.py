"""Parametrized KG operations."""
import pytest
from aios_core.knowledge_graph import KnowledgeGraph

@pytest.mark.parametrize("rel_type", ["knows", "parent_of", "depends_on", "references"])
def test_edge_types(rel_type):
    kg = KnowledgeGraph()
    kg.add_node("a", {})
    kg.add_node("b", {})
    assert kg.add_edge("a", "b", rel_type) is not None

@pytest.mark.parametrize("n_nodes", [1, 3, 10, 50])
def test_bulk_nodes(n_nodes):
    kg = KnowledgeGraph()
    for i in range(n_nodes):
        kg.add_node(f"n{i}", {"idx": i})
    assert kg.stats() is not None
