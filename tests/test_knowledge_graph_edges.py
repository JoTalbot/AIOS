from aios_core.knowledge_graph import KnowledgeGraph
def test_edges():
    kg = KnowledgeGraph()
    kg.add_node('a', {}); kg.add_node('b', {})
    e = kg.add_edge('a', 'b', 'rel')
    assert e is not None