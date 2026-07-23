"""Edge: KG long chain."""
from aios_core.knowledge_graph import KnowledgeGraph
def test_long_chain():
    kg = KnowledgeGraph()
    for i in range(100):
        kg.add_node(f"n{i}", {"idx": i})
    for i in range(99):
        kg.add_edge(f"n{i}", f"n{i+1}", "next")
    assert kg.stats() is not None
