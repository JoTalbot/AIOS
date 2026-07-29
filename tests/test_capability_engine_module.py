"""Comprehensive behavioral tests for aios_core/capability_engine.py"""

from __future__ import annotations

from unittest.mock import patch

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


# ── Transition DAG enforcement ──────────────────────────


class TestTransitionDAG:
    def test_registered_to_testing(self, engine):
        engine.register(name="cap1", description="d", handler=None, capability_type="action")
        result = engine.transition("cap1", new_status="testing")
        assert result["success"] is True
        assert result["old_status"] == "registered"
        assert result["new_status"] == "testing"

    def test_testing_to_tested(self, engine):
        engine.register(name="cap2", description="d", handler=None, capability_type="action")
        engine.transition("cap2", new_status="testing")
        result = engine.transition("cap2", new_status="tested")
        assert result["success"] is True
        assert result["old_status"] == "testing"
        assert result["new_status"] == "tested"

    def test_tested_to_validated(self, engine):
        engine.register(name="cap3", description="d", handler=None, capability_type="action")
        engine.transition("cap3", new_status="testing")
        engine.transition("cap3", new_status="tested")
        result = engine.transition("cap3", new_status="validated")
        assert result["success"] is True
        assert result["old_status"] == "tested"
        assert result["new_status"] == "validated"

    def test_validated_to_trusted(self, engine):
        engine.register(name="cap4", description="d", handler=None, capability_type="action")
        engine.transition("cap4", new_status="testing")
        engine.transition("cap4", new_status="tested")
        engine.transition("cap4", new_status="validated")
        result = engine.transition("cap4", new_status="trusted")
        assert result["success"] is True
        assert result["old_status"] == "validated"
        assert result["new_status"] == "trusted"

    def test_full_chain_registered_to_trusted(self, engine):
        engine.register(name="cap_chain", description="d", handler=None, capability_type="action")
        assert engine.transition("cap_chain", new_status="testing")["success"] is True
        assert engine.transition("cap_chain", new_status="tested")["success"] is True
        assert engine.transition("cap_chain", new_status="validated")["success"] is True
        assert engine.transition("cap_chain", new_status="trusted")["success"] is True

    def test_trusted_to_discovered_is_invalid(self, engine):
        engine.register(name="cap5", description="d", handler=None, capability_type="action")
        engine.transition("cap5", new_status="testing")
        engine.transition("cap5", new_status="tested")
        engine.transition("cap5", new_status="validated")
        engine.transition("cap5", new_status="trusted")
        result = engine.transition("cap5", new_status="discovered")
        assert result["success"] is False
        assert "is not allowed" in result["error"]

    def test_registered_to_trusted_is_invalid(self, engine):
        engine.register(name="cap6", description="d", handler=None, capability_type="action")
        result = engine.transition("cap6", new_status="trusted")
        assert result["success"] is False
        assert "is not allowed" in result["error"]

    def test_discovered_to_registered(self, engine):
        engine.discover(name="cap7", description="d", capability_type="sensor")
        result = engine.transition("cap7", new_status="registered")
        assert result["success"] is True
        assert result["old_status"] == "discovered"
        assert result["new_status"] == "registered"

    def test_deprecated_to_retired(self, engine):
        engine.register(name="cap8", description="d", handler=None, capability_type="action")
        engine.transition("cap8", new_status="deprecated")
        result = engine.transition("cap8", new_status="retired")
        assert result["success"] is True
        assert result["new_status"] == "retired"

    def test_any_status_can_retire(self, engine):
        engine.register(name="cap9", description="d", handler=None, capability_type="action")
        engine.transition("cap9", new_status="testing")
        result = engine.transition("cap9", new_status="retired")
        assert result["success"] is True
        assert result["new_status"] == "retired"

    def test_same_status_no_op(self, engine):
        engine.register(name="cap10", description="d", handler=None, capability_type="action")
        result = engine.transition("cap10", new_status="registered")
        assert result["success"] is True
        assert result["new_status"] == "registered"

    def test_transition_nonexistent_capability(self, engine):
        result = engine.transition("nonexistent", new_status="testing")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_invalid_status_value(self, engine):
        engine.register(name="cap11", description="d", handler=None, capability_type="action")
        result = engine.transition("cap11", new_status="invalid_status")
        assert result["success"] is False
        assert "Invalid status" in result["error"]


# ── Authority check on execute ──────────────────────────


class TestAuthorityCheck:
    def test_execute_with_insufficient_authority(self, engine):
        engine.register(
            name="admin_cap",
            description="admin only",
            handler=None,
            capability_type="action",
            required_authority="admin",
        )
        result = engine.execute("admin_cap", input_data={}, authority="user")
        assert result["success"] is False
        assert "insufficient" in result["error"].lower()

    def test_execute_with_sufficient_authority(self, engine):
        engine.register(
            name="user_cap",
            description="user level",
            handler=lambda d: {"result": d["value"] * 2},
            capability_type="action",
            required_authority="user",
        )
        result = engine.execute("user_cap", input_data={"value": 5}, authority="user")
        assert result["success"] is True
        assert result["result"] == {"result": 10}

    def test_execute_with_higher_authority(self, engine):
        engine.register(
            name="sys_cap",
            description="system level",
            handler=lambda d: {"result": d["value"] * 3},
            capability_type="action",
            required_authority="system",
        )
        result = engine.execute("sys_cap", input_data={"value": 4}, authority="root")
        assert result["success"] is True
        assert result["result"] == {"result": 12}


# ── Execute with handler timing ─────────────────────────


class TestExecutionTiming:
    def test_execute_handler_returns_correct_result(self, engine):
        engine.register(
            name="double_cap",
            description="doubles value",
            handler=lambda d: {"value": d["value"] * 2},
            capability_type="action",
        )
        result = engine.execute("double_cap", input_data={"value": 5})
        assert result["success"] is True
        assert result["result"] == {"value": 10}

    def test_execute_handler_timing_has_duration(self, engine):
        engine.register(
            name="timed_cap",
            description="timed cap",
            handler=lambda d: {"value": d["value"] + 1},
            capability_type="action",
        )
        result = engine.execute("timed_cap", input_data={"value": 10})
        assert result["success"] is True
        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], (int, float))
        assert result["duration_ms"] >= 0

    def test_execute_with_monotonic_patched_timing(self, engine):
        call_count = {"n": 0}

        def fake_monotonic():
            call_count["n"] += 1
            return float(call_count["n"]) * 0.5

        engine.register(
            name="patched_cap",
            description="patched timing",
            handler=lambda d: {"value": d["value"] * 2},
            capability_type="action",
        )
        with patch("aios_core.capability_engine.time.monotonic", fake_monotonic):
            result = engine.execute("patched_cap", input_data={"value": 5})
        assert result["success"] is True
        assert result["result"] == {"value": 10}
        assert result["duration_ms"] == 500.0


# ── Compose chaining ────────────────────────────────────


class TestComposeChaining:
    def test_compose_chain_execution(self, engine):
        engine.register(
            name="cap_add10",
            description="adds 10",
            handler=lambda d: {"value": d["value"] + 10},
            capability_type="action",
        )
        engine.register(
            name="cap_mul2",
            description="multiplies by 2",
            handler=lambda d: {"value": d["value"] * 2},
            capability_type="action",
        )
        result = engine.compose(
            composition_name="chain",
            capabilities=[{"name": "cap_add10"}, {"name": "cap_mul2"}],
            description="add then multiply",
        )
        assert result["success"] is True
        execute_result = engine.execute("chain", input_data={"value": 5})
        assert execute_result["success"] is True
        assert execute_result["result"] == {"value": 30}

    def test_compose_with_mapping(self, engine):
        engine.register(
            name="step_a",
            description="step A",
            handler=lambda d: {"output_a": d["x"] + 5},
            capability_type="action",
        )
        engine.register(
            name="step_b",
            description="step B",
            handler=lambda d: {"output_b": d["output_a"] * 3},
            capability_type="action",
        )
        result = engine.compose(
            composition_name="mapped_chain",
            capabilities=[
                {"name": "step_a", "mapping": {"x": "x"}},
                {"name": "step_b", "mapping": {"output_a": "output_a"}},
            ],
            description="mapped compose",
        )
        assert result["success"] is True
        execute_result = engine.execute("mapped_chain", input_data={"x": 10})
        assert execute_result["success"] is True
        assert execute_result["result"] == {"output_b": 45}

    def test_compose_rejects_empty_steps(self, engine):
        result = engine.compose(
            composition_name="empty_chain",
            capabilities=[],
            description="should fail",
        )
        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_compose_rejects_missing_step(self, engine):
        result = engine.compose(
            composition_name="missing_step",
            capabilities=[{"name": "does_not_exist"}],
            description="missing step",
        )
        assert result["success"] is False
        assert "not found" in result["error"]


# ── Search filters ──────────────────────────────────────


class TestSearchFilters:
    def test_search_by_capability_type(self, engine):
        engine.register(name="s1", description="d", handler=None, capability_type="action")
        engine.register(name="s2", description="d", handler=None, capability_type="sensor")
        results = engine.search(capability_type="action")
        assert len(results) == 1
        assert results[0]["name"] == "s1"

    def test_search_by_status(self, engine):
        engine.register(name="st1", description="d", handler=None, capability_type="action")
        engine.transition("st1", new_status="testing")
        results = engine.search(status="testing")
        assert len(results) == 1
        assert results[0]["name"] == "st1"

    def test_search_by_risk_level(self, engine):
        engine.register(
            name="high1",
            description="d",
            handler=None,
            capability_type="action",
            risk_level="high",
        )
        engine.register(
            name="low1",
            description="d",
            handler=None,
            capability_type="action",
            risk_level="low",
        )
        results = engine.search(risk_level="high")
        assert len(results) == 1
        assert results[0]["name"] == "high1"

    def test_search_by_tag(self, engine):
        engine.register(
            name="tagged1",
            description="d",
            handler=None,
            capability_type="action",
            tags=["urgent", "v2"],
        )
        engine.register(
            name="tagged2",
            description="d",
            handler=None,
            capability_type="action",
            tags=["normal"],
        )
        results = engine.search(tag="urgent")
        assert len(results) == 1
        assert results[0]["name"] == "tagged1"

    def test_search_by_query(self, engine):
        engine.register(name="searchable_cap", description="find me", handler=None, capability_type="action")
        engine.register(name="other_cap", description="unrelated", handler=None, capability_type="action")
        results = engine.search(query="find")
        assert len(results) == 1
        assert results[0]["name"] == "searchable_cap"

    def test_search_combined_filters(self, engine):
        engine.register(
            name="match1",
            description="d",
            handler=None,
            capability_type="action",
            tags=["tag_a"],
            risk_level="high",
        )
        engine.transition("match1", new_status="testing")
        engine.transition("match1", new_status="tested")
        engine.transition("match1", new_status="validated")
        engine.transition("match1", new_status="trusted")
        engine.register(
            name="match2",
            description="d",
            handler=None,
            capability_type="sensor",
            tags=["tag_a"],
            risk_level="high",
        )
        engine.transition("match2", new_status="testing")
        engine.transition("match2", new_status="tested")
        engine.transition("match2", new_status="validated")
        engine.transition("match2", new_status="trusted")
        engine.register(
            name="nomatch",
            description="d",
            handler=None,
            capability_type="action",
            tags=["tag_b"],
            risk_level="low",
        )
        results = engine.search(capability_type="action", status="trusted", risk_level="high", limit=10)
        assert len(results) == 1
        assert results[0]["name"] == "match1"

    def test_search_limit(self, engine):
        for i in range(10):
            engine.register(
                name=f"limit_cap_{i}",
                description="d",
                handler=None,
                capability_type="action",
            )
        results = engine.search(capability_type="action", limit=3)
        assert len(results) <= 3


# ── Suggest capabilities heuristic ──────────────────────


class TestSuggestCapabilities:
    def test_suggest_improved_for_high_failure_rate(self, engine):
        cap_engine = CapabilityEngine(db=None)
        cap_engine.register(
            name="flaky",
            description="flaky cap",
            handler=lambda d: d["value"],
            capability_type="action",
        )
        cap_engine._in_memory["flaky"]["metrics"] = {
            "execution_count": 50,
            "failure_count": 35,
            "success_count": 15,
            "avg_duration_ms": 5.0,
            "last_executed": None,
        }
        suggestions = cap_engine.suggest_capabilities(limit=5)
        improved = [s for s in suggestions if s["name"].startswith("improved_")]
        assert len(improved) >= 1
        assert improved[0]["reason"] == "high_failure_rate"

    def test_suggest_empty_when_no_high_failures(self, engine):
        cap_engine = CapabilityEngine(db=None)
        cap_engine.register(
            name="reliable",
            description="reliable cap",
            handler=lambda d: d["value"],
            capability_type="action",
        )
        cap_engine._in_memory["reliable"]["metrics"] = {
            "execution_count": 50,
            "failure_count": 1,
            "success_count": 49,
            "avg_duration_ms": 2.0,
            "last_executed": None,
        }
        suggestions = cap_engine.suggest_capabilities(limit=5)
        improved = [s for s in suggestions if s["name"].startswith("improved_")]
        assert len(improved) == 0


# ── Stats aggregation ───────────────────────────────────


class TestStats:
    def test_stats_total_and_by_status(self, engine):
        engine.register(name="stat1", description="d", handler=None, capability_type="action")
        engine.register(name="stat2", description="d", handler=None, capability_type="action")
        engine.register(name="stat3", description="d", handler=None, capability_type="sensor")
        engine.transition("stat1", new_status="testing")
        s = engine.stats()
        assert s["total_capabilities"] == 3
        assert s["by_status"]["registered"] == 2
        assert s["by_status"]["testing"] == 1

    def test_stats_by_type(self, engine):
        engine.register(name="s1", description="d", handler=None, capability_type="action")
        engine.register(name="s2", description="d", handler=None, capability_type="action")
        engine.register(name="s3", description="d", handler=None, capability_type="sensor")
        s = engine.stats()
        assert s["by_type"]["action"] == 2
        assert s["by_type"]["sensor"] == 1

    def test_stats_with_executions(self, engine):
        engine.register(
            name="exec_cap",
            description="d",
            handler=lambda d: {"result": d["value"]},
            capability_type="action",
        )
        engine.execute("exec_cap", input_data={"value": 1})
        s = engine.stats()
        assert s["total_capabilities"] == 1
        assert s["handlers_loaded"] == 1


# ── Registration & retrieval ────────────────────────────


class TestRegistration:
    def test_register_returns_dict(self, engine):
        result = engine.register(
            name="new_cap",
            description="A new capability",
            handler=None,
            capability_type="action",
        )
        assert isinstance(result, dict)
        assert result["name"] == "new_cap"
        assert result["status"] == "registered"

    def test_register_stores_handler(self, engine):
        handler = lambda d: d["value"] * 2
        engine.register(name="with_handler", description="d", handler=handler, capability_type="action")
        result = engine.execute("with_handler", input_data={"value": 3})
        assert result["success"] is True
        assert result["result"] == 6

    def test_get_capability_returns_registered_cap(self, engine):
        engine.register(name="get_reg", description="d", handler=None, capability_type="action")
        cap = engine.get_capability("get_reg")
        assert cap is not None
        assert cap["name"] == "get_reg"
        assert cap["status"] == "registered"

    def test_get_nonexistent_returns_none(self, engine):
        assert engine.get_capability("does_not_exist") is None

    def test_discover_sets_discovered_status(self, engine):
        result = engine.discover(name="disco", description="d", capability_type="sensor")
        assert result["status"] == "discovered"

    def test_register_preserves_risk_and_authority(self, engine):
        result = engine.register(
            name="secure_cap",
            description="d",
            handler=None,
            capability_type="action",
            risk_level="high",
            required_authority="admin",
        )
        assert result["risk_level"] == "high"
        assert result["required_authority"] == "admin"

    def test_register_preserves_tags_and_dependencies(self, engine):
        result = engine.register(
            name="dep_cap",
            description="d",
            handler=None,
            capability_type="action",
            tags=["core", "v1"],
            dependencies=["other_cap"],
        )
        assert result["tags"] == ["core", "v1"]
        assert result["dependencies"] == ["other_cap"]

    def test_deprecate_updates_status(self, engine):
        engine.register(name="old_cap", description="d", handler=None, capability_type="action")
        result = engine.deprecate("old_cap", reason="superseded")
        assert result["success"] is True
        assert result["new_status"] == "deprecated"

    def test_retire_marks_inactive(self, engine):
        engine.register(name="dead_cap", description="d", handler=None, capability_type="action")
        result = engine.retire("dead_cap", reason="no longer needed")
        assert result["success"] is True
        cap = engine.get_capability("dead_cap")
        assert cap["status"] == "retired"

    def test_execute_nonexistent_capability(self, engine):
        result = engine.execute("no_such_cap", input_data={})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_execute_deprecated_capability_fails(self, engine):
        engine.register(
            name="dead_handler",
            description="d",
            handler=lambda d: d["value"],
            capability_type="action",
        )
        engine.deprecate("dead_handler")
        result = engine.execute("dead_handler", input_data={"value": 1})
        assert result["success"] is False
        assert "cannot be executed" in result["error"]
