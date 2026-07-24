"""Comprehensive tests for aios_core/planner.py"""

from __future__ import annotations

import pytest

from aios_core.planner import PlanStatus, Planner, StepStatus
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def planner(db):
    return Planner(db)


# ── Plan CRUD ──────────────────────────────────────────────────


class TestPlanCRUD:
    def test_create_plan(self, planner):
        plan = planner.create_plan(name="deploy", description="Deploy v2")
        assert plan.name == "deploy"
        assert plan.description == "Deploy v2"
        assert plan.id

    def test_save_and_get_plan(self, planner):
        plan = planner.create_plan(name="save_me", description="d")
        planner.save_plan(plan)
        fetched = planner.get_plan(plan.id)
        assert fetched is not None
        assert fetched.name == "save_me"

    def test_get_nonexistent_plan(self, planner):
        assert planner.get_plan("nope") is None

    def test_list_plans_empty(self, planner):
        result = planner.list_plans()
        assert isinstance(result, list)

    def test_list_plans_after_create(self, planner):
        p1 = planner.create_plan(name="p1", description="d1")
        p2 = planner.create_plan(name="p2", description="d2")
        planner.save_plan(p1)
        planner.save_plan(p2)
        plans = planner.list_plans()
        assert len(plans) >= 2

    def test_delete_plan(self, planner):
        plan = planner.create_plan(name="delete_me", description="d")
        planner.save_plan(plan)
        assert planner.delete_plan(plan.id) is True
        assert planner.get_plan(plan.id) is None

    def test_delete_nonexistent(self, planner):
        assert planner.delete_plan("nope") is False


# ── Steps ──────────────────────────────────────────────────────


class TestPlanSteps:
    def test_add_step(self, planner):
        plan = planner.create_plan(name="p", description="d")
        step = planner.add_step(plan, step_type="action", params={"k": "v"}, name="step1")
        assert step.name == "step1"
        assert step.params == {"k": "v"}

    def test_multiple_steps(self, planner):
        plan = planner.create_plan(name="p", description="d")
        planner.add_step(plan, step_type="action", params={}, name="s1")
        planner.add_step(plan, step_type="check", params={}, name="s2")
        planner.add_step(plan, step_type="deploy", params={}, name="s3")
        assert len(plan.steps) == 3

    def test_add_dependency(self, planner):
        plan = planner.create_plan(name="p", description="d")
        s1 = planner.add_step(plan, step_type="action", params={}, name="s1")
        s2 = planner.add_step(plan, step_type="action", params={}, name="s2")
        edge = planner.add_dependency(plan, s1.id, s2.id)
        assert edge is not None


# ── Validation ─────────────────────────────────────────────────


class TestPlanValidation:
    def test_validate_empty_plan(self, planner):
        plan = planner.create_plan(name="empty", description="d")
        result = planner.validate_plan(plan)
        assert isinstance(result, dict)

    def test_validate_plan_with_steps(self, planner):
        plan = planner.create_plan(name="p", description="d")
        planner.add_step(plan, step_type="action", params={}, name="s1")
        result = planner.validate_plan(plan)
        assert isinstance(result, dict)


# ── Execution layers ───────────────────────────────────────────


class TestExecutionLayers:
    def test_get_execution_layers_single(self, planner):
        plan = planner.create_plan(name="p", description="d")
        planner.add_step(plan, step_type="action", params={}, name="s1")
        layers = planner.get_execution_layers(plan)
        assert isinstance(layers, list)
        assert len(layers) >= 1

    def test_get_execution_layers_with_deps(self, planner):
        plan = planner.create_plan(name="p", description="d")
        s1 = planner.add_step(plan, step_type="action", params={}, name="s1")
        s2 = planner.add_step(plan, step_type="action", params={}, name="s2")
        planner.add_dependency(plan, s1.id, s2.id)
        layers = planner.get_execution_layers(plan)
        assert len(layers) >= 2


# ── Step status transitions ────────────────────────────────────


class TestStepTransitions:
    def test_mark_step_running(self, planner):
        plan = planner.create_plan(name="p", description="d")
        step = planner.add_step(plan, step_type="action", params={}, name="s1")
        result = planner.mark_step_running(plan, step.id)
        assert result is not None

    def test_mark_step_completed(self, planner):
        plan = planner.create_plan(name="p", description="d")
        step = planner.add_step(plan, step_type="action", params={}, name="s1")
        planner.mark_step_running(plan, step.id)
        result = planner.mark_step_completed(plan, step.id)
        assert result is not None

    def test_mark_step_failed(self, planner):
        plan = planner.create_plan(name="p", description="d")
        step = planner.add_step(plan, step_type="action", params={}, name="s1")
        result = planner.mark_step_failed(plan, step.id, error="boom")
        assert result is not None


# ── Progress ───────────────────────────────────────────────────


class TestProgress:
    def test_get_plan_progress_empty(self, planner):
        plan = planner.create_plan(name="p", description="d")
        progress = planner.get_plan_progress(plan)
        assert isinstance(progress, dict)

    def test_get_plan_progress_with_steps(self, planner):
        plan = planner.create_plan(name="p", description="d")
        planner.add_step(plan, step_type="action", params={}, name="s1")
        planner.add_step(plan, step_type="action", params={}, name="s2")
        progress = planner.get_plan_progress(plan)
        assert isinstance(progress, dict)


# ── Stats & other ──────────────────────────────────────────────


class TestPlannerMisc:
    def test_stats(self, planner):
        s = planner.stats()
        assert isinstance(s, dict)

    def test_estimate_duration(self, planner):
        plan = planner.create_plan(name="p", description="d")
        planner.add_step(plan, step_type="action", params={}, name="s1")
        result = planner.estimate_duration(plan)
        assert isinstance(result, dict)

    def test_get_ready_steps(self, planner):
        plan = planner.create_plan(name="p", description="d")
        planner.add_step(plan, step_type="action", params={}, name="s1")
        ready = planner.get_ready_steps(plan)
        assert isinstance(ready, list)

    def test_score_plan(self, planner):
        plan = planner.create_plan(name="p", description="d")
        result = planner.score_plan(plan)
        assert isinstance(result, dict)

    def test_generate_multi_agent_plan(self, planner):
        plan = planner.generate_multi_agent_plan(goal="deploy", agents=["a1", "a2"])
        assert plan is not None
        assert len(plan.steps) >= 2
