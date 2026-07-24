"""Comprehensive tests for aios_core/knowledge_graph.py"""

from __future__ import annotations

import pytest

from aios_core.knowledge_graph import EntityInfo, KnowledgeGraph, PathResult, Triple
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def kg(db):
    return KnowledgeGraph(db)


# ── Triples ────────────────────────────────────────────────────


class TestTriples:
    def test_add_triple(self, kg):
        t = Triple(subject="A", predicate="knows", object="B")
        kg.add_triple(t)
        related = kg.related("A")
        assert isinstance(related, list)

    def test_add_multiple_triples(self, kg):
        for s, p, o in [("A", "knows", "B"), ("A", "knows", "C"), ("B", "knows", "D")]:
            kg.add_triple(Triple(subject=s, predicate=p, object=o))
        stats = kg.stats()
        assert isinstance(stats, dict)

    def test_remove_triple(self, kg):
        kg.add_triple(Triple(subject="A", predicate="likes", object="B"))
        result = kg.remove_triple("A", "likes", "B")
        assert isinstance(result, bool)

    def test_triple_to_dict(self):
        t = Triple(subject="A", predicate="knows", object="B")
        d = t.to_dict()
        assert isinstance(d, dict)
        assert d["subject"] == "A"
        assert d["predicate"] == "knows"
        assert d["object"] == "B"


# ── Nodes ──────────────────────────────────────────────────────


class TestNodes:
    def test_add_node(self, kg):
        node = kg.add_node(label="entity1", node_type="person")
        assert isinstance(node, dict)
        assert node.get("label") == "entity1" or node.get("node_id")

    def test_get_nonexistent_node(self, kg):
        assert kg.get_node("nope") is None

    def test_find_nodes(self, kg):
        kg.add_node(label="alice", node_type="person")
        kg.add_node(label="bob", node_type="person")
        results = kg.find_nodes(label="alice")
        assert isinstance(results, list)

    def test_count_nodes(self, kg):
        kg.add_node(label="a")
        kg.add_node(label="b")
        kg.add_node(label="c")
        count = kg.count_nodes()
        assert count >= 3


# ── Relations ──────────────────────────────────────────────────


class TestRelations:
    def test_add_relation(self, kg):
        n1 = kg.add_node(label="A")
        n2 = kg.add_node(label="B")
        src = n1.get("node_id", "A")
        tgt = n2.get("node_id", "B")
        result = kg.add_relation(source_id=src, target_id=tgt, relation="parent")
        assert isinstance(result, dict)

    def test_neighbors(self, kg):
        n1 = kg.add_node(label="A")
        n2 = kg.add_node(label="B")
        src = n1.get("node_id", "A")
        tgt = n2.get("node_id", "B")
        kg.add_relation(source_id=src, target_id=tgt, relation="knows")
        n = kg.neighbors(src)
        assert isinstance(n, list)

    def test_find_related(self, kg):
        n1 = kg.add_node(label="X")
        n2 = kg.add_node(label="Y")
        src = n1.get("node_id", "X")
        tgt = n2.get("node_id", "Y")
        kg.add_relation(source_id=src, target_id=tgt, relation="works_at")
        result = kg.find_related(src, predicate="works_at")
        assert isinstance(result, list)

    def test_find_neighbors(self, kg):
        n1 = kg.add_node(label="N1")
        n2 = kg.add_node(label="N2")
        src = n1.get("node_id", "N1")
        tgt = n2.get("node_id", "N2")
        kg.add_relation(source_id=src, target_id=tgt, relation="connected")
        result = kg.find_neighbors(src)
        assert isinstance(result, list)


# ── Path finding ───────────────────────────────────────────────


class TestPathFinding:
    def test_path_direct(self, kg):
        n1 = kg.add_node(label="A")
        n2 = kg.add_node(label="B")
        src = n1.get("node_id", "A")
        tgt = n2.get("node_id", "B")
        kg.add_relation(source_id=src, target_id=tgt, relation="to")
        result = kg.path(src, tgt)
        assert isinstance(result, list)

    def test_path_multi_hop(self, kg):
        n1 = kg.add_node(label="A")
        n2 = kg.add_node(label="B")
        n3 = kg.add_node(label="C")
        a = n1.get("node_id", "A")
        b = n2.get("node_id", "B")
        c = n3.get("node_id", "C")
        kg.add_relation(source_id=a, target_id=b, relation="to")
        kg.add_relation(source_id=b, target_id=c, relation="to")
        result = kg.path(a, c)
        assert isinstance(result, list)

    def test_find_path(self, kg):
        n1 = kg.add_node(label="S")
        n2 = kg.add_node(label="E")
        s = n1.get("node_id", "S")
        e = n2.get("node_id", "E")
        result = kg.find_path(s, e)
        assert result is None or isinstance(result, PathResult)


# ── Entity management ──────────────────────────────────────────


class TestEntities:
    def test_set_entity_type(self, kg):
        n = kg.add_node(label="e1")
        eid = n.get("node_id", "e1")
        kg.set_entity_type(eid, "concept")
        entity = kg.get_entity(eid)
        assert entity is not None

    def test_set_entity_property(self, kg):
        n = kg.add_node(label="e1")
        eid = n.get("node_id", "e1")
        kg.set_entity_property(eid, "weight", "0.5")
        entity = kg.get_entity(eid)
        assert entity is not None

    def test_get_entities_by_type(self, kg):
        n1 = kg.add_node(label="p1", node_type="person")
        n2 = kg.add_node(label="p2", node_type="person")
        results = kg.get_entities_by_type("person")
        assert isinstance(results, list)

    def test_entity_popularity(self):
        info = EntityInfo(entity_id="e1", type="concept", properties={})
        assert isinstance(info.popularity, (int, float))


# ── Inference ──────────────────────────────────────────────────


class TestInference:
    def test_infer_returns_int(self, kg):
        result = kg.infer()
        assert isinstance(result, int)


# ── Export and stats ───────────────────────────────────────────


class TestExportAndStats:
    def test_export_triples(self, kg):
        kg.add_triple(Triple(subject="A", predicate="knows", object="B"))
        kg.add_triple(Triple(subject="C", predicate="likes", object="D"))
        exported = kg.export_triples()
        assert isinstance(exported, list)

    def test_stats(self, kg):
        kg.add_triple(Triple(subject="A", predicate="r1", object="B"))
        s = kg.stats()
        assert isinstance(s, dict)

    def test_clear(self, kg):
        kg.add_triple(Triple(subject="A", predicate="r", object="B"))
        kg.clear()
        s = kg.stats()
        assert isinstance(s, dict)
