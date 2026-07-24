"""Comprehensive tests for aios_core/capability_engine.py"""

from __future__ import annotations

import pytest

from aios_core.capability_engine import CapabilityEngine
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def engine(db):
    return CapabilityEngine(db)


# ── Registration ───────────────────────────────────────────────


class TestRegister:
    def test_register_capability(self, engine):
        result = engine.register(
            name="test_cap",
            description="Test capability",
            handler=None,
            capability_type="action",
        )
        assert isinstance(result, dict)
        assert result.get("name") == "test_cap" or "test_cap" in str(result)

    def test_register_with_schemas(self, engine):
        result = engine.register(
            name="typed_cap",
            description="Typed",
            handler=None,
            capability_type="action",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        assert isinstance(result, dict)

    def test_register_with_tags(self, engine):
        result = engine.register(
            name="tagged",
            description="Tagged cap",
            handler=None,
            capability_type="action",
            tags=["important", "v2"],
        )
        assert isinstance(result, dict)

    def test_register_with_risk(self, engine):
        result = engine.register(
            name="risky",
            description="High risk",
            handler=None,
            capability_type="action",
            risk_level="high",
            required_authority="admin",
        )
        assert isinstance(result, dict)


# ── Discovery & Search ─────────────────────────────────────────


class TestDiscovery:
    def test_discover(self, engine):
        result = engine.discover(name="new_cap", description="Auto-discovered", capability_type="sensor")
        assert isinstance(result, dict)

    def test_search_empty(self, engine):
        results = engine.search(query="nonexistent")
        assert isinstance(results, list)

    def test_search_after_register(self, engine):
        engine.register(name="searchable", description="Find me", handler=None, capability_type="action")
        results = engine.search(query="searchable")
        assert isinstance(results, list)

    def test_search_by_type(self, engine):
        engine.register(name="cap1", description="d", handler=None, capability_type="sensor")
        engine.register(name="cap2", description="d", handler=None, capability_type="action")
        results = engine.search(capability_type="sensor")
        assert isinstance(results, list)

    def test_get_capability(self, engine):
        engine.register(name="get_me", description="d", handler=None, capability_type="action")
        result = engine.get_capability("get_me")
        assert result is not None

    def test_get_nonexistent(self, engine):
        assert engine.get_capability("nope") is None


# ── Lifecycle ──────────────────────────────────────────────────


class TestLifecycle:
    def test_transition(self, engine):
        engine.register(name="trans", description="d", handler=None, capability_type="action")
        result = engine.transition("trans", new_status="active", reason="testing")
        assert isinstance(result, dict)

    def test_deprecate(self, engine):
        engine.register(name="old", description="d", handler=None, capability_type="action")
        result = engine.deprecate("old", reason="superseded")
        assert isinstance(result, dict)

    def test_retire(self, engine):
        engine.register(name="dead", description="d", handler=None, capability_type="action")
        result = engine.retire("dead", reason="no longer needed")
        assert isinstance(result, dict)


# ── Execution ──────────────────────────────────────────────────


class TestExecution:
    def test_execute(self, engine):
        engine.register(name="run_me", description="d", handler=None, capability_type="action")
        result = engine.execute("run_me", input_data={"key": "val"}, agent_id="test", authority="system")
        assert isinstance(result, dict)


# ── Composition ────────────────────────────────────────────────


class TestComposition:
    def test_compose(self, engine):
        engine.register(name="step1", description="d", handler=None, capability_type="action")
        engine.register(name="step2", description="d", handler=None, capability_type="action")
        result = engine.compose(
            composition_name="pipeline",
            capabilities=[{"name": "step1"}, {"name": "step2"}],
            description="Two-step pipeline",
        )
        assert isinstance(result, dict)


# ── Stats & suggestions ───────────────────────────────────────


class TestMisc:
    def test_stats(self, engine):
        s = engine.stats()
        assert isinstance(s, dict)

    def test_stats_with_capabilities(self, engine):
        engine.register(name="a", description="d", handler=None, capability_type="action")
        engine.register(name="b", description="d", handler=None, capability_type="sensor")
        s = engine.stats()
        assert isinstance(s, dict)

    def test_suggest_capabilities(self, engine):
        result = engine.suggest_capabilities(limit=5)
        assert isinstance(result, list)
