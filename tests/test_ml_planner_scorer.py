"""Tests for MLPlannerScorer v4.0-alpha"""

from aios_core import Database, Orchestrator
from aios_core.ml_planner_scorer import MLPlannerScorer


def test_ml_scorer_basic():
    db = Database(":memory:")
    orch = Orchestrator(db=db)
    scorer = orch.ml_scorer

    plan = orch.planner.create_plan("ml_test", goal="test ml scoring")
    orch.planner.add_step(plan, "memory", {"action": "store"})
    orch.planner.add_step(plan, "reason", {})

    result = scorer.score_plan(plan, orch.planner)

    assert "ml_score" in result
    assert "ml_features" in result
    assert 0.0 <= result["ml_score"] <= 1.0


def test_ml_optimize():
    db = Database(":memory:")
    orch = Orchestrator(db=db)
    scorer = orch.ml_scorer

    plan = orch.planner.create_plan("optimize_test", goal="optimize me")
    orch.planner.add_step(plan, "tool", {"cmd": "echo"})

    result = scorer.optimize_plan(plan, orch.planner)
    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)


def test_orchestrator_ml_integration():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    plan = orch.planner.create_plan("orch_ml", goal="test integration")
    orch.planner.add_step(plan, "memory", {"action": "store"})

    score = orch.score_plan_with_ml(plan)
    assert "ml_score" in score

    opt = orch.optimize_plan_with_ml(plan)
    assert "optimized" in opt
