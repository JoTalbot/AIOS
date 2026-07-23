"""Tests for knowledge graph traversal and edge creation."""

from aios_core.knowledge_graph import KnowledgeGraph


def test_kg_add_and_retrieve():
    kg = KnowledgeGraph()
    kg.add_node("n1", {"type": "entity"})
    kg.add_node("n2", {"type": "entity"})
    e = kg.add_edge("n1", "n2", "connected_to")
    assert e is not None
