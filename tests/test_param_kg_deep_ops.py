"""Parametrized: KG deep operations."""
import pytest
from aios_core.knowledge_graph import KnowledgeGraph

@pytest.mark.parametrize("n_nodes,n_edges", [(2,1),(5,4),(10,9),(20,19)])
def test_chain_graph(n_nodes, n_edges):
    kg = KnowledgeGraph()
    for i in range(n_nodes): kg.add_node(f"n{i}", {"i": i})
    for i in range(n_edges): kg.add_edge(f"n{i}", f"n{i+1}", "next")
    assert kg.stats() is not None

@pytest.mark.parametrize("degrees", [1,3,5,10])
def test_star_graph(degrees):
    kg = KnowledgeGraph()
    kg.add_node("center", {})
    for i in range(degrees):
        kg.add_node(f"leaf{i}", {})
        kg.add_edge("center", f"leaf{i}", "has")
    assert kg.stats() is not None
