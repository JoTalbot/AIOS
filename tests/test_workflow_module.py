"""Comprehensive tests for aios_core/workflow.py"""

from __future__ import annotations

import pytest

from aios_core.workflow import (
    CompensationAction,
    DAGExecutor,
    RetryPolicy,
    TimeoutPolicy,
    Workflow,
    WorkflowEngine,
    WorkflowStep,
    WorkflowTemplate,
)


# ── RetryPolicy ────────────────────────────────────────────────


class TestRetryPolicy:
    def test_create(self):
        p = RetryPolicy(max_retries=3, initial_delay=1.0)
        assert p.max_retries == 3
        assert p.initial_delay == 1.0

    def test_compute_delay(self):
        p = RetryPolicy(max_retries=3, initial_delay=1.0, max_delay=60.0)
        d = p.compute_delay(1)
        assert isinstance(d, (int, float))
        assert d >= 0

    def test_should_retry(self):
        p = RetryPolicy(max_retries=3, initial_delay=1.0, retryable_exceptions=["ValueError"])
        assert p.should_retry("ValueError") is True
        assert p.should_retry("TypeError") is False

    def test_should_retry_no_exceptions(self):
        p = RetryPolicy(max_retries=3)
        assert p.should_retry("Anything") is True


# ── TimeoutPolicy ──────────────────────────────────────────────


class TestTimeoutPolicy:
    def test_create(self):
        p = TimeoutPolicy(timeout_seconds=30.0)
        assert p.timeout_seconds == 30.0

    def test_total_timeout(self):
        p = TimeoutPolicy(timeout_seconds=30.0, grace_period=5.0)
        result = p.total_timeout()
        assert isinstance(result, (int, float))


# ── WorkflowStep ───────────────────────────────────────────────


class TestWorkflowStep:
    def test_create_step(self):
        step = WorkflowStep(name="s1", action=lambda: "ok")
        assert step.name == "s1"

    def test_duration(self):
        step = WorkflowStep(name="s1", action=lambda: "ok")
        assert isinstance(step.duration(), (int, float))

    def test_step_with_params(self):
        step = WorkflowStep(name="s1", action=lambda x: x, params={"key": "val"})
        assert step.params == {"key": "val"}

    def test_step_with_dependencies(self):
        step = WorkflowStep(name="s2", action=lambda: "ok", depends_on=["s1"])
        assert "s1" in step.depends_on

    def test_step_with_retry(self):
        rp = RetryPolicy(max_retries=2)
        step = WorkflowStep(name="s1", action=lambda: "ok", retry_policy=rp)
        assert step.retry_policy.max_retries == 2


# ── Workflow ───────────────────────────────────────────────────


class TestWorkflow:
    def test_create_workflow(self):
        w = Workflow(name="test_wf")
        assert w.name == "test_wf"

    def test_add_step(self):
        w = Workflow(name="wf")
        step = WorkflowStep(name="s1", action=lambda: "ok")
        w.add_step(step)
        assert len(w.steps) >= 1

    def test_remove_step(self):
        w = Workflow(name="wf")
        step = WorkflowStep(name="s1", action=lambda: "ok")
        w.add_step(step)
        w.remove_step(step.id)


# ── WorkflowEngine ─────────────────────────────────────────────


class TestWorkflowEngine:
    def test_create_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(name="my_wf")
        assert wf is not None
        assert wf.name == "my_wf"

    def test_add_step(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(name="wf")
        step = engine.add_step(
            workflow_id=wf.id,
            name="step1",
            action=lambda: "done",
        )
        assert step is not None

    def test_get_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(name="wf")
        fetched = engine.get_workflow(wf.id)
        assert fetched is not None

    def test_list_workflows(self):
        engine = WorkflowEngine()
        engine.create_workflow(name="wf1")
        engine.create_workflow(name="wf2")
        wfs = engine.list_workflows()
        assert len(wfs) >= 2

    def test_register_template(self):
        engine = WorkflowEngine()
        tmpl = WorkflowTemplate(name="deploy_tmpl")
        engine.register_template(tmpl)
        templates = engine.list_templates()
        assert len(templates) >= 1

    def test_create_from_template(self):
        engine = WorkflowEngine()
        tmpl = WorkflowTemplate(name="tmpl")
        engine.register_template(tmpl)
        wf = engine.create_from_template("tmpl", name="from_tmpl")
        assert wf is not None

    def test_execute_simple(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(name="simple")
        engine.add_step(wf.id, name="s1", action=lambda: "ok")
        result = engine.execute(wf.id)
        assert isinstance(result, dict)

    def test_cancel(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(name="cancel_me")
        engine.cancel(wf.id)

    def test_stats(self):
        engine = WorkflowEngine()
        engine.create_workflow(name="wf1")
        s = engine.stats()
        assert isinstance(s, dict)


# ── DAGExecutor ────────────────────────────────────────────────


class TestDAGExecutor:
    def test_compute_layers(self):
        executor = DAGExecutor()
        s1 = WorkflowStep(name="s1", action=lambda: "a")
        s2 = WorkflowStep(name="s2", action=lambda: "b", depends_on=[s1.id])
        layers = executor.compute_layers({s1.id: s1, s2.id: s2})
        assert isinstance(layers, list)
        assert len(layers) >= 2

    def test_execute_workflow(self):
        executor = DAGExecutor()
        wf = Workflow(name="dag_test")
        step = WorkflowStep(name="s1", action=lambda: "result")
        wf.add_step(step)
        result = executor.execute_workflow(wf)
        assert result is not None
