"""Tests for advanced Planner v3.0 features"""

from aios_core import Database, Orchestrator


def test_plan_scoring():
    db = Database(":memory:")
    orch = Orchestrator(db=db)
    planner = orch.planner

    plan = planner.create_plan("test_score", goal="score test")
    planner.add_step(plan, "memory", {"action": "store"})
    planner.add_step(plan, "tool", {"cmd": "echo"})

    score = planner.score_plan(plan)
    assert "score" in score
    assert 0.0 <= score["score"] <= 1.0


def test_multi_agent_plan_generation():
    db = Database(":memory:")
    orch = Orchestrator(db=db)
    planner = orch.planner

    plan = planner.generate_multi_agent_plan(
        goal="analyze data", agents=["researcher", "analyst", "reviewer"]
    )

    assert len(plan.steps) >= 5  # coordination + 3 agents + aggregation
    assert any("coordination" in s.name for s in plan.steps)
    assert any("aggregation" in s.name for s in plan.steps)
