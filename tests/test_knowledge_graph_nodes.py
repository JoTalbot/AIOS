"""KG node operations."""
from aios_core.knowledge_graph import KnowledgeGraph
def test_nodes(): kg = KnowledgeGraph(); kg.add_node("n1", {"t":"e"}); kg.add_node("n2", {"t":"e"}); assert kg.stats() is not None
