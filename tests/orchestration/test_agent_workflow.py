"""Tests for agent workflow orchestration."""


def test_workflow_roles_order():
    workflow = ["planner", "executor", "evaluator"]
    assert workflow == ["planner", "executor", "evaluator"]


def test_workflow_pipeline_shape():
    pipeline = {
        "input": "goal",
        "steps": ["plan", "execute", "evaluate"],
        "output": "feedback",
    }

    assert pipeline["steps"][-1] == "evaluate"
    assert pipeline["output"] == "feedback"
