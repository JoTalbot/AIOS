"""Tests for AIOS Phase 1 — Persistence & Infrastructure.

Tests Database, Config, AuditLogger, ApprovalManager, MemoryManager,
KnowledgeGraph, and RuntimePolicy integration with persistence.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from aios_core.storage import Database
from aios_core.config import load_config, AIOSConfig, _deep_merge, _apply_env_overrides
from aios_core.audit_logger import AuditLogger
from aios_core.approval_manager import ApprovalManager
from aios_core.memory_manager import MemoryManager
from aios_core.knowledge_graph import KnowledgeGraph


def _make_db():
    """Create an in-memory test database."""
    return Database(":memory:")


# ======================================================================
# Database Tests
# ======================================================================


class TestDatabase(unittest.TestCase):
    def test_creates_tables(self):
        db = _make_db()
        tables = db.tables()
        self.assertIn("audit_events", tables)
        self.assertIn("approvals", tables)
        self.assertIn("memory_items", tables)
        self.assertIn("kg_nodes", tables)
        self.assertIn("kg_edges", tables)
        self.assertIn("evolution_records", tables)
        self.assertIn("schema_version", tables)
        db.close()

    def test_stats(self):
        db = _make_db()
        stats = db.stats()
        self.assertEqual(stats["schema_version"], 3)
        self.assertEqual(stats["tables"]["audit_events"], 0)
        self.assertEqual(stats["tables"]["kg_nodes"], 0)
        db.close()

    def test_transaction_commit(self):
        db = _make_db()
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO audit_events (id, event_type, data, timestamp) " "VALUES (?, ?, ?, ?)",
                ("test-1", "test", "{}", "2026-01-01T00:00:00Z"),
            )
        self.assertEqual(db.row_count("audit_events"), 1)
        db.close()

    def test_transaction_rollback(self):
        db = _make_db()
        try:
            with db.transaction() as conn:
                conn.execute(
                    "INSERT INTO audit_events (id, event_type, data, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    ("test-2", "test", "{}", "2026-01-01T00:00:00Z"),
                )
                raise ValueError("force rollback")
        except ValueError:
            pass
        self.assertEqual(db.row_count("audit_events"), 0)
        db.close()

    def test_query(self):
        db = _make_db()
        db.execute(
            "INSERT INTO audit_events (id, event_type, data, timestamp) " "VALUES (?, ?, ?, ?)",
            ("q1", "type_a", '{"x":1}', "2026-01-01T00:00:00Z"),
        )
        rows = db.query("SELECT * FROM audit_events WHERE event_type = ?", ("type_a",))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "q1")
        db.close()

    def test_query_one(self):
        db = _make_db()
        result = db.query_one("SELECT * FROM audit_events WHERE id = ?", ("nope",))
        self.assertIsNone(result)
        db.close()

    def test_new_id_unique(self):
        ids = {Database.new_id() for _ in range(100)}
        self.assertEqual(len(ids), 100)

    def test_json_roundtrip(self):
        data = {"key": "value", "nested": {"a": 1}}
        json_str = Database.to_json(data)
        restored = Database.from_json(json_str)
        self.assertEqual(restored, data)


# ======================================================================
# Config Tests
# ======================================================================


class TestConfig(unittest.TestCase):
    def test_load_default_config(self):
        config = load_config()
        self.assertIsInstance(config, AIOSConfig)
        self.assertEqual(config.database.path, "aios.db")
        self.assertEqual(config.approval.timeout_seconds, 86400)
        self.assertEqual(config.logging.level, "INFO")

    def test_resolve_path(self):
        config = load_config()
        resolved = config.resolve_path("docs/constitution")
        # Path should resolve to an existing directory with constitution files
        self.assertTrue(os.path.isdir(resolved))
        self.assertTrue(os.path.exists(os.path.join(resolved, "ARTICLE-I-IDENTITY.md")))

    def test_deep_merge(self):
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 99, "e": 4}, "f": 5}
        result = _deep_merge(base, override)
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"]["c"], 99)
        self.assertEqual(result["b"]["d"], 3)
        self.assertEqual(result["b"]["e"], 4)
        self.assertEqual(result["f"], 5)

    def test_from_dict(self):
        config = AIOSConfig.from_dict(
            {
                "database": {"path": "test.db"},
                "approval": {"timeout_seconds": 3600},
            }
        )
        self.assertEqual(config.database.path, "test.db")
        self.assertEqual(config.approval.timeout_seconds, 3600)
        # Defaults preserved
        self.assertEqual(config.audit.retention_days, 90)


# ======================================================================
# AuditLogger Tests
# ======================================================================


class TestAuditLogger(unittest.TestCase):
    def setUp(self):
        self.db = _make_db()
        self.logger = AuditLogger(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_record_and_query(self):
        self.logger.record({"type": "test_event", "data": "hello"})
        results = self.logger.query(event_type="test_event")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "test_event")
        self.assertIn("id", results[0])
        self.assertIn("timestamp", results[0])

    def test_query_by_agent(self):
        self.logger.record({"type": "action", "agent_id": "agent-1", "decision": "ALLOW"})
        self.logger.record({"type": "action", "agent_id": "agent-2", "decision": "DENY"})
        results = self.logger.query(agent_id="agent-1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["agent_id"], "agent-1")

    def test_query_by_decision(self):
        self.logger.record({"type": "exec", "decision": "ALLOW"})
        self.logger.record({"type": "exec", "decision": "DENY"})
        self.logger.record({"type": "exec", "decision": "ALLOW"})
        results = self.logger.query(decision="ALLOW")
        self.assertEqual(len(results), 2)

    def test_count(self):
        self.logger.record({"type": "a"})
        self.logger.record({"type": "a"})
        self.logger.record({"type": "b"})
        self.assertEqual(self.logger.count("a"), 2)
        self.assertEqual(self.logger.count(), 3)

    def test_stats(self):
        self.logger.record({"type": "exec", "decision": "ALLOW"})
        self.logger.record({"type": "exec", "decision": "DENY"})
        self.logger.record({"type": "other"})
        stats = self.logger.stats()
        self.assertEqual(stats["total_events"], 3)
        self.assertEqual(stats["by_decision"]["ALLOW"], 1)
        self.assertEqual(stats["by_decision"]["DENY"], 1)
        self.assertEqual(stats["storage"], "sqlite")

    def test_fallback_no_db(self):
        logger = AuditLogger(db=None, file_path="/dev/null")
        logger.record({"type": "test"})
        results = logger.query(event_type="test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "test")

    def test_auto_assigns_id_and_timestamp(self):
        event = self.logger.record({"type": "test"})
        self.assertIn("id", event)
        self.assertIn("timestamp", event)
        self.assertTrue(len(event["id"]) > 8)


# ======================================================================
# ApprovalManager Tests
# ======================================================================


class TestApprovalManager(unittest.TestCase):
    def setUp(self):
        self.db = _make_db()
        self.mgr = ApprovalManager(db=self.db, timeout_seconds=3600)

    def tearDown(self):
        self.db.close()

    def test_request_approval(self):
        approval = self.mgr.request({"goal": "test", "scope": "system"})
        self.assertIn("id", approval)
        self.assertEqual(approval["status"], "pending")
        self.assertIn("requested_at", approval)

    def test_approve(self):
        approval = self.mgr.request({"goal": "test"})
        result = self.mgr.approve(approval["id"])
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["resolved_by"], "human")
        self.assertIsNotNone(result["resolved_at"])

    def test_deny(self):
        approval = self.mgr.request({"goal": "test"})
        result = self.mgr.deny(approval["id"])
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "denied")

    def test_double_approve_idempotent(self):
        approval = self.mgr.request({"goal": "test"})
        self.mgr.approve(approval["id"])
        result = self.mgr.approve(approval["id"])
        self.assertEqual(result["status"], "approved")  # Not error

    def test_approve_nonexistent(self):
        result = self.mgr.approve("nonexistent-id")
        self.assertIsNone(result)

    def test_get_pending(self):
        self.mgr.request({"goal": "a"})
        self.mgr.request({"goal": "b"})
        pending = self.mgr.get_pending()
        self.assertEqual(len(pending), 2)

    def test_pending_after_approve(self):
        approval = self.mgr.request({"goal": "test"})
        self.mgr.approve(approval["id"])
        pending = self.mgr.get_pending()
        self.assertEqual(len(pending), 0)

    def test_history(self):
        self.mgr.request({"goal": "a"})
        a = self.mgr.request({"goal": "b"})
        self.mgr.approve(a["id"])
        history = self.mgr.history()
        self.assertEqual(len(history), 2)

    def test_history_filter(self):
        self.mgr.request({"goal": "a"})
        a = self.mgr.request({"goal": "b"})
        self.mgr.approve(a["id"])
        approved = self.mgr.history(status="approved")
        pending = self.mgr.history(status="pending")
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(pending), 1)

    def test_stats(self):
        self.mgr.request({"goal": "a"})
        a = self.mgr.request({"goal": "b"})
        self.mgr.deny(a["id"])
        stats = self.mgr.stats()
        self.assertEqual(stats["by_status"]["pending"], 1)
        self.assertEqual(stats["by_status"]["denied"], 1)

    def test_request_with_evaluation_id(self):
        approval = self.mgr.request(
            {"goal": "test"},
            evaluation_id="eval-123",
            validation_data={"valid": False},
        )
        self.assertEqual(approval["evaluation_id"], "eval-123")
        self.assertEqual(approval["validation"]["valid"], False)

    def test_uuid_ids_are_unique(self):
        a1 = self.mgr.request({"goal": "a"})
        a2 = self.mgr.request({"goal": "b"})
        self.assertNotEqual(a1["id"], a2["id"])


# ======================================================================
# MemoryManager Tests
# ======================================================================


class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self.db = _make_db()
        self.mm = MemoryManager(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_store_and_retrieve(self):
        item = self.mm.store(
            content={"key": "value"},
            category="operational",
            tags=["test", "demo"],
        )
        self.assertIn("id", item)
        self.assertEqual(item["category"], "operational")

        retrieved = self.mm.retrieve(item["id"])
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["content"]["key"], "value")
        self.assertIn("test", retrieved["tags"])

    def test_invalid_category_defaults_to_operational(self):
        item = self.mm.store({"x": 1}, category="invalid")
        self.assertEqual(item["category"], "operational")

    def test_three_categories(self):
        p = self.mm.store({"data": "personal"}, category="personal")
        o = self.mm.store({"data": "operational"}, category="operational")
        c = self.mm.store({"data": "constitutional"}, category="constitutional")

        self.assertEqual(self.mm.count("personal"), 1)
        self.assertEqual(self.mm.count("operational"), 1)
        self.assertEqual(self.mm.count("constitutional"), 1)
        self.assertEqual(self.mm.count(), 3)

    def test_search(self):
        self.mm.store({"description": "alpha beta gamma"}, tags=["math"])
        self.mm.store({"description": "delta epsilon"}, tags=["physics"])
        results = self.mm.search("alpha")
        self.assertEqual(len(results), 1)

    def test_search_by_tag(self):
        self.mm.store({"x": 1}, tags=["important", "v2"])
        self.mm.store({"x": 2}, tags=["v2"])
        results = self.mm.search(tag="important")
        self.assertEqual(len(results), 1)

    def test_search_by_category(self):
        self.mm.store({"x": 1}, category="personal")
        self.mm.store({"x": 2}, category="operational")
        self.mm.store({"x": 3}, category="operational")
        results = self.mm.search(category="operational")
        self.assertEqual(len(results), 2)

    def test_update(self):
        item = self.mm.store({"version": 1}, category="operational")
        updated = self.mm.update(item["id"], content={"version": 2})
        self.assertIsNotNone(updated)
        self.assertEqual(updated["content"]["version"], 2)

    def test_update_constitutional_fails(self):
        item = self.mm.store({"law": "immutable"}, category="constitutional")
        updated = self.mm.update(item["id"], content={"law": "changed"})
        # Should return unchanged
        self.assertEqual(updated["content"]["law"], "immutable")

    def test_delete(self):
        item = self.mm.store({"x": 1}, category="operational")
        result = self.mm.delete(item["id"])
        self.assertTrue(result)
        self.assertIsNone(self.mm.retrieve(item["id"]))

    def test_delete_constitutional_fails(self):
        item = self.mm.store({"law": "x"}, category="constitutional")
        result = self.mm.delete(item["id"])
        self.assertFalse(result)
        self.assertIsNotNone(self.mm.retrieve(item["id"]))

    def test_ttl(self):
        item = self.mm.store({"temp": True}, ttl_seconds=0)
        # Item with ttl_seconds=0 should be immediately expired
        self.assertIsNotNone(item["expires_at"])
        self.mm.cleanup_expired()
        self.assertEqual(self.mm.count(), 0)

    def test_stats(self):
        self.mm.store({"a": 1}, category="personal")
        self.mm.store({"b": 2}, category="operational")
        stats = self.mm.stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["by_category"]["personal"], 1)

    def test_no_db_returns_empty(self):
        mm = MemoryManager(db=None)
        self.assertEqual(mm.search("anything"), [])
        self.assertIsNone(mm.retrieve("any-id"))
        self.assertEqual(mm.count(), 0)


# ======================================================================
# KnowledgeGraph Tests
# ======================================================================


class TestKnowledgeGraph(unittest.TestCase):
    def setUp(self):
        self.db = _make_db()
        self.kg = KnowledgeGraph(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_add_node(self):
        node = self.kg.add_node("Security", node_type="article", properties={"num": 5})
        self.assertIn("id", node)
        self.assertEqual(node["label"], "Security")
        self.assertEqual(node["type"], "article")
        retrieved = self.kg.get_node(node["id"])
        self.assertIsNotNone(retrieved)

    def test_add_node_upsert(self):
        nid = "fixed-id"
        self.kg.add_node("Old", node_id=nid)
        self.kg.add_node("New", node_id=nid)
        node = self.kg.get_node(nid)
        self.assertEqual(node["label"], "New")

    def test_find_nodes(self):
        self.kg.add_node("Alpha Node", node_type="concept")
        self.kg.add_node("Beta Node", node_type="concept")
        self.kg.add_node("Gamma", node_type="rule")
        results = self.kg.find_nodes(node_type="concept")
        self.assertEqual(len(results), 2)

    def test_find_by_label(self):
        self.kg.add_node("Memory Separation", node_type="principle")
        self.kg.add_node("Limited Autonomy", node_type="principle")
        results = self.kg.find_nodes(label="Memory")
        self.assertEqual(len(results), 1)

    def test_add_relation(self):
        n1 = self.kg.add_node("Node A")
        n2 = self.kg.add_node("Node B")
        edge = self.kg.add_relation(n1["id"], n2["id"], "depends_on")
        self.assertEqual(edge["source"], n1["id"])
        self.assertEqual(edge["target"], n2["id"])
        self.assertEqual(edge["relation"], "depends_on")

    def test_related(self):
        a = self.kg.add_node("A")
        b = self.kg.add_node("B")
        c = self.kg.add_node("C")
        self.kg.add_relation(a["id"], b["id"], "rel1")
        self.kg.add_relation(a["id"], c["id"], "rel2")
        related = self.kg.related(a["id"])
        self.assertEqual(len(related), 2)

    def test_related_by_relation_type(self):
        a = self.kg.add_node("A")
        b = self.kg.add_node("B")
        c = self.kg.add_node("C")
        self.kg.add_relation(a["id"], b["id"], "type_x")
        self.kg.add_relation(a["id"], c["id"], "type_y")
        related = self.kg.related(a["id"], relation="type_x")
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]["target"], b["id"])

    def test_neighbors(self):
        a = self.kg.add_node("A")
        b = self.kg.add_node("B")
        c = self.kg.add_node("C")
        d = self.kg.add_node("D")
        self.kg.add_relation(a["id"], b["id"], "r")
        self.kg.add_relation(b["id"], c["id"], "r")
        self.kg.add_relation(c["id"], d["id"], "r")
        neighbors = self.kg.neighbors(a["id"], depth=2)
        ids = {n["id"] for n in neighbors}
        self.assertIn(b["id"], ids)
        self.assertIn(c["id"], ids)
        self.assertNotIn(d["id"], ids)  # depth=2 from A: B and C

    def test_path(self):
        a = self.kg.add_node("A")
        b = self.kg.add_node("B")
        c = self.kg.add_node("C")
        self.kg.add_relation(a["id"], b["id"], "r")
        self.kg.add_relation(b["id"], c["id"], "r")
        path = self.kg.path(a["id"], c["id"])
        self.assertEqual(len(path), 2)
        self.assertEqual(path[0]["target"], b["id"])
        self.assertEqual(path[1]["target"], c["id"])

    def test_no_path(self):
        a = self.kg.add_node("A")
        b = self.kg.add_node("B")
        path = self.kg.path(a["id"], b["id"])
        self.assertEqual(path, [])

    def test_auto_creates_nodes(self):
        edge = self.kg.add_relation("node-x", "node-y", "test")
        self.assertIsNotNone(self.kg.get_node("node-x"))
        self.assertIsNotNone(self.kg.get_node("node-y"))

    def test_stats(self):
        self.kg.add_node("A", node_type="concept")
        self.kg.add_node("B", node_type="rule")
        self.kg.add_relation("A-id", "B-id", "refs")
        stats = self.kg.stats()
        self.assertEqual(stats["nodes"], 4)  # A, B, A-id, B-id (auto-created)
        self.assertGreater(stats["edges"], 0)

    def test_no_db(self):
        kg = KnowledgeGraph(db=None)
        self.assertEqual(kg.find_nodes("anything"), [])
        self.assertEqual(kg.count_nodes(), 0)
        self.assertEqual(kg.related("x"), [])


# ======================================================================
# RuntimePolicy Integration with Persistence
# ======================================================================


class TestRuntimePolicyPersistence(unittest.TestCase):
    """Test that RuntimePolicy v3.1 works with SQLite persistence."""

    @classmethod
    def setUpClass(cls):
        cls.db = _make_db()
        from aios_core.runtime_policy import RuntimePolicy

        cls.runtime = RuntimePolicy(
            constitution_dir=os.path.join(PROJECT_ROOT, "docs", "constitution"),
            policies_dir=os.path.join(PROJECT_ROOT, "policies"),
            db=cls.db,
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_allow_persists_audit(self):
        result = self.runtime.request_execution(
            {
                "goal": "Read metrics",
                "scope": "monitoring",
                "risk": "low",
                "audit_log": True,
                "agent_id": "agent-persist-1",
                "authority": "reader",
            }
        )
        self.assertTrue(result["allowed"])
        # Verify it's in the DB
        events = self.runtime.audit.query(agent_id="agent-persist-1")
        self.assertGreater(len(events), 0)

    def test_review_creates_persistent_approval(self):
        result = self.runtime.request_execution(
            {
                "goal": "Deploy module",
                "scope": "production",
                "risk": "high",
                "audit_log": True,
                "agent_id": "agent-persist-2",
                "authority": "operator",
            }
        )
        self.assertEqual(result["decision"], "REVIEW")
        approval_id = result["approval_id"]
        self.assertIsNotNone(approval_id)

        # Approve via UUID
        approved = self.runtime.approve(approval_id)
        self.assertEqual(approved["status"], "approved")

    def test_deny_persistent_approval(self):
        result = self.runtime.request_execution(
            {
                "goal": "Critical change",
                "scope": "core",
                "risk": "critical",
                "audit_log": True,
                "agent_id": "agent-persist-3",
                "authority": "senior",
            }
        )
        approval_id = result["approval_id"]
        denied = self.runtime.deny(approval_id)
        self.assertEqual(denied["status"], "denied")

    def test_get_pending_approvals(self):
        self.runtime.request_execution(
            {
                "goal": "Pending test",
                "scope": "test",
                "risk": "high",
                "audit_log": True,
                "agent_id": "agent-pending",
                "authority": "op",
            }
        )
        pending = self.runtime.get_pending_approvals()
        self.assertGreater(len(pending), 0)

    def test_audit_stats_persistent(self):
        stats = self.runtime.audit.stats()
        self.assertEqual(stats["storage"], "sqlite")
        self.assertGreater(stats["total_events"], 0)

    def test_approval_stats_persistent(self):
        stats = self.runtime.approvals.stats()
        self.assertEqual(stats["storage"], "sqlite")

    def test_db_stats(self):
        stats = self.runtime.db.stats()
        self.assertGreater(stats["tables"]["audit_events"], 0)


if __name__ == "__main__":
    unittest.main()
