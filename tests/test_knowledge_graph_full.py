"""Knowledge graph full tests."""
from aios_core.knowledge_graph import KnowledgeGraph
def test_kg_operations():
    kg = KnowledgeGraph()
    kg.add_node("a", {"type": "t"})
    kg.add_node("b", {"type": "t"})
    assert kg.add_edge("a", "b", "rel") is not None
    assert kg.stats() is not None
