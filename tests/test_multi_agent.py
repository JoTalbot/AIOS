"""Tests for MultiAgentOrchestrator v4.0-alpha"""

from aios_core import Orchestrator, Database


def test_form_team():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    team = orch.multi_agent.form_team(
        goal="analyze market data",
        agents=["researcher", "analyst", "writer"],
        leader="researcher"
    )

    assert team.team_id is not None
    assert len(team.agents) == 3


def test_create_team_task():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    team = orch.multi_agent.form_team("build report", ["agent_a", "agent_b"])
    task = orch.multi_agent.create_team_task(team.team_id, "generate_report")

    assert task is not None
    assert "TEAM" in task.name


def test_conflict_resolution():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    team = orch.multi_agent.form_team("test", ["a", "b"])
    result = orch.multi_agent.resolve_conflict(team.team_id, "priority conflict")

    assert result["success"] is True
    assert "resolution" in result


def test_orchestrator_multi_agent_stats():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    orch.multi_agent.form_team("demo", ["x", "y"])
    stats = orch.stats()

    assert "multi_agent" in stats["subsystems"]
    assert stats["subsystems"]["multi_agent"]["total_teams"] >= 1
