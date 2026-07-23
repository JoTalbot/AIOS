"""Tests for Knowledge Graph and Memory Manager."""

from aios_core.knowledge_graph import KnowledgeGraph


def test_kg_stats():
    kg = KnowledgeGraph()
    s = kg.stats()
    assert isinstance(s, dict)


def test_kg_add_node():
    kg = KnowledgeGraph()
    node = kg.add_node("test_node", {"type": "concept"})
    assert node["id"] == "test_node"


def test_kg_add_edge():
    kg = KnowledgeGraph()
    kg.add_node("a", {})
    kg.add_node("b", {})
    edge = kg.add_edge("a", "b", "knows")
    assert edge is not None
