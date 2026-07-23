"""Deep KG — complex graph patterns."""
from aios_core.knowledge_graph import KnowledgeGraph
def test_graph_chain():
    kg = KnowledgeGraph()
    for c in "abcdef": kg.add_node(c, {"type": "entity"})
    pairs = [("a","b"), ("b","c"), ("c","d"), ("d","e"), ("e","f")]
    for s, t in pairs: assert kg.add_edge(s, t, "next") is not None
    assert kg.stats() is not None
def test_multi_edge_types():
    kg = KnowledgeGraph()
    kg.add_node("x", {})
    kg.add_node("y", {})
    assert kg.add_edge("x", "y", "knows") is not None
    assert kg.add_edge("x", "y", "trusts") is not None
