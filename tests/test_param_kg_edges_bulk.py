"""Parametrized KG edge types bulk."""
import pytest
from aios_core.knowledge_graph import KnowledgeGraph

@pytest.mark.parametrize("rel", ["knows","trusts","depends_on","references","cites","derives_from"])
def test_edge_creation(rel):
    kg = KnowledgeGraph()
    kg.add_node("src", {"type":"entity"})
    kg.add_node("dst", {"type":"entity"})
    assert kg.add_edge("src", "dst", rel) is not None

@pytest.mark.parametrize("n", [1,5,10,20,50,100])
def test_bulk_nodes(n):
    kg = KnowledgeGraph()
    for i in range(n): kg.add_node(f"n{i}", {"idx": i})
    assert kg.stats() is not None
