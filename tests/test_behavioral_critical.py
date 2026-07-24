"""Behavioral tests for critical AIOS modules: Planner, Storage, Orchestrator, API integrations."""

from __future__ import annotations

import json
import os

from aios_core.orchestrator import Orchestrator, TaskStatus
from aios_core.planner import Planner, PlanStatus, StepStatus
from aios_core.storage import Database


def _make_planner() -> Planner:
    """Create a Planner with an in-memory DB so save/get/list work."""
    return Planner(db=Database(":memory:"))


# ==========================================================================
# Planner behavioral tests
# ==========================================================================

class TestPlannerCreatePlan:
    """Test plan creation and lifecycle."""

    def test_create_plan_basic(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Test Plan", goal="Test goal")
        assert plan.name == "Test Plan"
        assert plan.goal == "Test goal"
        assert plan.status == PlanStatus.DRAFT
        assert len(plan.steps) == 0

    def test_save_and_get_plan(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Saved Plan", goal="Save test")
        saved = planner.save_plan(plan)
        retrieved = planner.get_plan(saved.id)
        assert retrieved is not None
        assert retrieved.name == "Saved Plan"

    def test_list_plans(self):
        planner = _make_planner()
        planner.save_plan(planner.create_plan(name="P1", goal="G1"))
        planner.save_plan(planner.create_plan(name="P2", goal="G2"))
        plans = planner.list_plans()
        assert len(plans) >= 2

    def test_list_plans_by_status(self):
        planner = _make_planner()
        planner.save_plan(planner.create_plan(name="Draft1", goal="G"))
        planner.save_plan(planner.create_plan(name="Draft2", goal="G"))
        drafts = planner.list_plans(status="draft")
        assert len(drafts) >= 2

    def test_delete_plan(self):
        planner = _make_planner()
        plan = planner.create_plan(name="ToDelete", goal="G")
        planner.save_plan(plan)
        result = planner.delete_plan(plan.id)
        assert result is True
        assert planner.get_plan(plan.id) is None


class TestPlannerAddSteps:
    """Test adding steps and dependencies."""

    def test_add_step(self):
        planner = _make_planner()
        plan = planner.create_plan(name="StepTest", goal="G")
        planner.add_step(plan, name="Step1", step_type="tool", params={"action": "test"})
        assert len(plan.steps) == 1
        assert plan.steps[0].name == "Step1"

    def test_add_multiple_steps(self):
        planner = _make_planner()
        plan = planner.create_plan(name="MultiStep", goal="G")
        planner.add_step(plan, name="S1", step_type="evaluate")
        planner.add_step(plan, name="S2", step_type="memory")
        planner.add_step(plan, name="S3", step_type="knowledge")
        assert len(plan.steps) == 3

    def test_add_dependency(self):
        planner = _make_planner()
        plan = planner.create_plan(name="DepTest", goal="G")
        s1 = planner.add_step(plan, name="First", step_type="tool")
        s2 = planner.add_step(plan, name="Second", step_type="tool")
        edge = planner.add_dependency(plan, source_step_id=s1.id, target_step_id=s2.id)
        assert edge.source_id == s1.id
        assert edge.target_id == s2.id

    def test_validate_plan_no_cycle(self):
        planner = _make_planner()
        plan = planner.create_plan(name="ValidPlan", goal="G")
        s1 = planner.add_step(plan, name="A", step_type="tool")
        s2 = planner.add_step(plan, name="B", step_type="tool")
        planner.add_dependency(plan, source_step_id=s1.id, target_step_id=s2.id)
        result = planner.validate_plan(plan)
        assert result["valid"] is True

    def test_validate_plan_with_cycle(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Cyclic", goal="G")
        s1 = planner.add_step(plan, name="A", step_type="tool")
        s2 = planner.add_step(plan, name="B", step_type="tool")
        s3 = planner.add_step(plan, name="C", step_type="tool")
        planner.add_dependency(plan, source_step_id=s1.id, target_step_id=s2.id)
        planner.add_dependency(plan, source_step_id=s2.id, target_step_id=s3.id)
        planner.add_dependency(plan, source_step_id=s3.id, target_step_id=s1.id)
        result = planner.validate_plan(plan)
        assert result["valid"] is False

    def test_execution_layers(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Layers", goal="G")
        s1 = planner.add_step(plan, name="A", step_type="tool")
        s2 = planner.add_step(plan, name="B", step_type="tool")
        s3 = planner.add_step(plan, name="C", step_type="tool")
        planner.add_dependency(plan, source_step_id=s1.id, target_step_id=s2.id)
        planner.add_dependency(plan, source_step_id=s2.id, target_step_id=s3.id)
        layers = planner.get_execution_layers(plan)
        assert len(layers) == 3

    def test_estimate_duration(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Duration", goal="G")
        planner.add_step(plan, name="S1", step_type="tool")
        planner.add_step(plan, name="S2", step_type="evaluate")
        result = planner.estimate_duration(plan, avg_step_ms=200)
        assert "estimated_ms" in result
        assert result["estimated_ms"] >= 200

    def test_get_ready_steps(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Ready", goal="G")
        s1 = planner.add_step(plan, name="NoDeps", step_type="tool")
        s2 = planner.add_step(plan, name="HasDeps", step_type="tool")
        planner.add_dependency(plan, source_step_id=s1.id, target_step_id=s2.id)
        ready = planner.get_ready_steps(plan)
        assert len(ready) == 1
        assert ready[0].name == "NoDeps"

    def test_mark_step_completed(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Complete", goal="G")
        s1 = planner.add_step(plan, name="S1", step_type="tool")
        planner.mark_step_completed(plan, s1.id)
        assert plan.steps[0].status == StepStatus.COMPLETED

    def test_mark_step_failed(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Fail", goal="G")
        s1 = planner.add_step(plan, name="S1", step_type="tool")
        planner.mark_step_failed(plan, s1.id, error="test error")
        assert plan.steps[0].status == StepStatus.FAILED
        assert plan.steps[0].error == "test error"

    def test_plan_progress(self):
        planner = _make_planner()
        plan = planner.create_plan(name="Progress", goal="G")
        s1 = planner.add_step(plan, name="S1", step_type="tool")
        planner.add_step(plan, name="S2", step_type="tool")
        planner.mark_step_completed(plan, s1.id)
        progress = planner.get_plan_progress(plan)
        assert progress["completed"] == 1
        assert progress["total_steps"] == 2

    def test_planner_stats(self):
        planner = _make_planner()
        planner.create_plan(name="P1", goal="G1")
        planner.create_plan(name="P2", goal="G2")
        stats = planner.stats()
        assert "version" in stats
        assert "storage" in stats


class TestPlannerScorePlan:
    """Test plan scoring."""

    def test_score_basic_plan(self):
        planner = _make_planner()
        plan = planner.create_plan(name="ScoreTest", goal="G")
        planner.add_step(plan, name="S1", step_type="tool")
        planner.add_step(plan, name="S2", step_type="evaluate")
        score = planner.score_plan(plan)
        assert "score" in score
        assert score["score"] >= 0


# ==========================================================================
# Storage behavioral tests
# ==========================================================================

class TestDatabaseBasic:
    """Test Database CRUD operations."""

    def test_init_memory(self):
        db = Database(db_path=":memory:")
        assert db is not None
        db.close()

    def test_init_file(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite")
        db = Database(db_path=db_path)
        db.close()
        assert os.path.exists(db_path)

    def test_tables(self):
        db = Database(db_path=":memory:")
        tables = db.tables()
        assert isinstance(tables, list)
        db.close()

    def test_execute_and_query(self):
        db = Database(db_path=":memory:")
        db.execute("CREATE TABLE test_items (id TEXT, name TEXT)")
        db.execute("INSERT INTO test_items VALUES (?, ?)", ("1", "item1"))
        rows = db.query("SELECT * FROM test_items")
        assert len(rows) == 1
        assert rows[0]["name"] == "item1"
        db.close()

    def test_query_one(self):
        db = Database(db_path=":memory:")
        db.execute("CREATE TABLE test_items (id TEXT, name TEXT)")
        db.execute("INSERT INTO test_items VALUES (?, ?)", ("1", "unique"))
        row = db.query_one("SELECT * FROM test_items WHERE id = ?", ("1",))
        assert row is not None
        assert row["name"] == "unique"
        db.close()

    def test_query_one_missing(self):
        db = Database(db_path=":memory:")
        db.execute("CREATE TABLE test_items (id TEXT, name TEXT)")
        row = db.query_one("SELECT * FROM test_items WHERE id = ?", ("missing",))
        assert row is None
        db.close()

    def test_row_count(self):
        db = Database(db_path=":memory:")
        db.execute("CREATE TABLE test_items (id TEXT)")
        db.execute("INSERT INTO test_items VALUES (?)", ("1",))
        db.execute("INSERT INTO test_items VALUES (?)", ("2",))
        count = db.row_count("test_items")
        assert count == 2
        db.close()

    def test_stats(self):
        db = Database(db_path=":memory:")
        stats = db.stats()
        assert "tables" in stats
        db.close()

    def test_transaction_commit(self):
        db = Database(db_path=":memory:")
        db.execute("CREATE TABLE test_items (id TEXT, name TEXT)")
        with db.transaction():
            db.execute("INSERT INTO test_items VALUES (?, ?)", ("1", "tx_item"))
        rows = db.query("SELECT * FROM test_items")
        assert len(rows) == 1
        db.close()

    def test_new_id(self):
        id1 = Database.new_id()
        id2 = Database.new_id()
        assert id1 != id2
        assert len(id1) > 0

    def test_now_iso(self):
        iso = Database.now_iso()
        assert "T" in iso

    def test_to_json_from_json(self):
        data = {"key": "value", "nums": [1, 2, 3]}
        j = Database.to_json(data)
        parsed = Database.from_json(j)
        assert parsed["key"] == "value"


# ==========================================================================
# Orchestrator behavioral tests
# ==========================================================================

class TestOrchestratorCreateTask:
    """Test task creation and lifecycle."""

    def test_create_task(self):
        orch = Orchestrator()
        task = orch.create_task(name="Test Task", description="A test task")
        assert task.name == "Test Task"
        assert task.status == TaskStatus.PENDING

    def test_get_task(self):
        orch = Orchestrator()
        task = orch.create_task(name="GetTask", description="test")
        retrieved = orch.get_task(task.id)
        assert retrieved is not None
        assert retrieved.name == "GetTask"

    def test_list_tasks(self):
        orch = Orchestrator()
        orch.create_task(name="T1", description="d")
        orch.create_task(name="T2", description="d")
        tasks = orch.list_tasks()
        assert len(tasks) >= 2

    def test_delete_task(self):
        orch = Orchestrator()
        task = orch.create_task(name="DelTask", description="test")
        result = orch.delete_task(task.id)
        assert result is True

    def test_add_step_to_task(self):
        orch = Orchestrator()
        task = orch.create_task(name="StepTask", description="test")
        orch.add_step(task, name="Step1", step_type="tool", params={"a": 1})
        assert len(task.steps) == 1

    def test_orchestrator_stats(self):
        orch = Orchestrator()
        orch.create_task(name="S1", description="d")
        stats = orch.stats()
        assert "total_tasks" in stats

    def test_orchestrator_close(self):
        orch = Orchestrator()
        orch.close()


class TestOrchestratorEvaluate:
    """Test constitutional evaluation."""

    def test_evaluate_action_deny_missing_fields(self):
        orch = Orchestrator()
        result = orch.evaluate({"action": "read", "target": "public_data"})
        assert isinstance(result, dict)
        # Without required fields (goal, scope, risk) it should deny
        assert result["allowed"] is False
        assert result["decision"] == "DENY"

    def test_evaluate_action_with_goal_scope_risk(self):
        orch = Orchestrator()
        result = orch.evaluate({
            "action": "read",
            "target": "public_data",
            "goal": "information retrieval",
            "scope": "public",
            "risk": "low",
        })
        assert isinstance(result, dict)
        # Should have a decision
        assert "decision" in result


# ==========================================================================
# API integration tests (OpenAPI spec + Dashboard)
# ==========================================================================

class TestOpenAPISpecIntegration:
    """Test OpenAPI spec generation integrated with swagger module."""

    def test_swagger_openapi_json_auto_generated(self):
        from aios_core.api.swagger import openapi_json

        spec_str = openapi_json()
        spec = json.loads(spec_str)
        assert "openapi" in spec
        assert spec["openapi"] == "3.0.3"
        assert "info" in spec

    def test_openapi_spec_dict(self):
        from aios_core.api.swagger import openapi_spec_dict

        spec = openapi_spec_dict()
        assert isinstance(spec, dict)
        assert "paths" in spec

    def test_swagger_html(self):
        from aios_core.api.swagger import swagger_html

        html = swagger_html()
        assert "swagger-ui" in html
        assert "<!DOCTYPE html>" in html

    def test_openapi_generator_register_aios_endpoints(self):
        from docs.openapi_spec import OpenAPIGenerator

        gen = OpenAPIGenerator()
        gen.register_aios_endpoints()
        spec = gen.generate_spec()
        assert "/health" in spec["paths"]
        assert "/tasks" in spec["paths"]
        assert len(spec["tags"]) == 3


class TestDashboardIntegration:
    """Test React Dashboard v3 integration."""

    def test_dashboard_html_file_exists(self):
        from pathlib import Path

        dash_path = Path("/home/user/AIOS/dashboard/index.html")
        assert dash_path.exists()

    def test_dashboard_app_creation(self):
        from aios_core.dashboard import create_dashboard
        from aios_core.orchestrator import Orchestrator

        orch = Orchestrator()
        app = create_dashboard(orch)
        assert app is not None
        route_paths = [r.path for r in app.routes]
        assert "/" in route_paths
        assert "/api/stats" in route_paths

    def test_dashboard_route_in_api(self):
        """Test /dashboard route is registered in main API routes."""
        from aios_core.api.app import AIOSAPI
        from aios_core.api.routes import register_routes

        api = AIOSAPI(db_path=":memory:", auth_required=False)
        routes = register_routes(api)
        route_paths = [r.path for r in routes]
        assert "/dashboard" in route_paths

    def test_dashboard_index_serves_react(self):
        """Test that AIOSDashboard.index serves the React v3 HTML."""

        from aios_core.dashboard import AIOSDashboard
        from aios_core.orchestrator import Orchestrator

        orch = Orchestrator()
        dash = AIOSDashboard(orch)
        from starlette.testclient import TestClient

        app = dash.create_app()
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        # Should contain React dashboard content or fallback
        assert "AIOS" in response.text
