"""test_knowledge_graph_scenario test."""
from aios_core.knowledge_graph import KnowledgeGraph

def test_graph_traversal():
    kg = KnowledgeGraph()
    for c in "abcde": kg.add_node(c, {"type": "entity"})
    kg.add_edge("a", "b", "parent")
    kg.add_edge("b", "c", "parent")
    kg.add_edge("a", "d", "knows")
    kg.add_edge("d", "e", "knows")
    assert kg.stats() is not None
