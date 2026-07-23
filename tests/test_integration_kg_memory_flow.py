"""Integration: KG + Memory cross-module test."""
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.memory_manager import MemoryManager
def test_kg_memory_integration():
    kg = KnowledgeGraph()
    mm = MemoryManager()
    mm.store({"entity": "node_a", "type": "concept"}, "system")
    kg.add_node("node_a", {"source": "memory"})
    assert kg.stats() is not None
    assert mm.stats() is not None
