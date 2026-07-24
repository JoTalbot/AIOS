"""Comprehensive tests for aios_core/orchestrator.py"""

from __future__ import annotations

import os
import pytest

from aios_core.orchestrator import Orchestrator, StepStatus, TaskStatus, TaskStep
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def orch(db, tmp_path):
    # Orchestrator needs constitution/policies dirs
    const_dir = tmp_path / "constitution"
    pol_dir = tmp_path / "policies"
    const_dir.mkdir()
    pol_dir.mkdir()
    # Create minimal constitution file
    (const_dir / "constitution.yaml").write_text("articles: []\n")
    o = Orchestrator(db=db, config=None, constitution_dir=str(const_dir), policies_dir=str(pol_dir))
    yield o
    o.close()


# ── Task creation ──────────────────────────────────────────────


class TestCreateTask:
    def test_create_basic_task(self, orch):
        task = orch.create_task(name="test", description="desc")
        assert task.name == "test"
        assert task.description == "desc"
        assert task.status == TaskStatus.PENDING

    def test_create_task_with_all_fields(self, orch):
        task = orch.create_task(
            name="full", description="full task",
            agent_id="agent-1", authority="admin", risk_level="low",
            metadata={"key": "value"},
        )
        assert task.agent_id == "agent-1"
        assert task.authority == "admin"
        assert task.risk_level == "low"
        assert task.metadata == {"key": "value"}

    def test_create_task_custom_id(self, orch):
        task = orch.create_task(name="custom", description="d", task_id="my-id")
        assert task.id == "my-id"

    def test_get_task(self, orch):
        task = orch.create_task(name="getme", description="d")
        fetched = orch.get_task(task.id)
        assert fetched is not None
        assert fetched.name == "getme"

    def test_get_nonexistent_task(self, orch):
        assert orch.get_task("nonexistent") is None

    def test_list_tasks_empty(self, orch):
        result = orch.list_tasks()
        assert isinstance(result, list)

    def test_list_tasks_after_create(self, orch):
        orch.create_task(name="t1", description="d1")
        orch.create_task(name="t2", description="d2")
        tasks = orch.list_tasks()
        assert len(tasks) >= 2

    def test_list_tasks_filtered_by_status(self, orch):
        orch.create_task(name="t1", description="d1")
        pending = orch.list_tasks(status=TaskStatus.PENDING)
        assert len(pending) >= 1

    def test_delete_task(self, orch):
        task = orch.create_task(name="delete_me", description="d")
        assert orch.delete_task(task.id) is True
        assert orch.get_task(task.id) is None

    def test_delete_nonexistent(self, orch):
        assert orch.delete_task("nope") is False


# ── Step management ────────────────────────────────────────────


class TestSteps:
    def test_add_step(self, orch):
        task = orch.create_task(name="s", description="d")
        step = orch.add_step(task, step_type="action", params={"url": "http://x"})
        assert step.step_type == "action"
        assert step.params == {"url": "http://x"}
        assert step.status == StepStatus.PENDING

    def test_add_step_with_name(self, orch):
        task = orch.create_task(name="s", description="d")
        step = orch.add_step(task, step_type="action", params={}, name="my_step", description="step desc")
        assert step.name == "my_step"
        assert step.description == "step desc"

    def test_multiple_steps(self, orch):
        task = orch.create_task(name="s", description="d")
        orch.add_step(task, step_type="action", params={"n": 1})
        orch.add_step(task, step_type="action", params={"n": 2})
        orch.add_step(task, step_type="action", params={"n": 3})
        assert len(task.steps) == 3


# ── Task data model ────────────────────────────────────────────


class TestTaskModel:
    def test_task_to_dict(self, orch):
        task = orch.create_task(name="dict", description="test dict")
        d = task.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "dict"
        assert d["description"] == "test dict"
        assert "id" in d

    def test_task_step_fields(self, orch):
        task = orch.create_task(name="s", description="d")
        step = orch.add_step(task, step_type="test", params={"a": 1})
        assert step.id
        assert step.step_type == "test"
        assert step.params == {"a": 1}
        assert step.status == StepStatus.PENDING


# ── Stats ──────────────────────────────────────────────────────


class TestStats:
    def test_stats_returns_dict(self, orch):
        s = orch.stats()
        assert isinstance(s, dict)

    def test_stats_with_tasks(self, orch):
        orch.create_task(name="t1", description="d")
        orch.create_task(name="t2", description="d")
        s = orch.stats()
        assert isinstance(s, dict)


# ── Evaluation ─────────────────────────────────────────────────


class TestEvaluation:
    def test_evaluate_returns_dict(self, orch):
        result = orch.evaluate({"action": "test", "target": "x"})
        assert isinstance(result, dict)
