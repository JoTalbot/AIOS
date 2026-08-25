"""Tests for agent quality feedback and conservative prompt optimization."""

from aios_core.openhands import AgentScoreboard, select_micro_agents, suggest_improvements


def test_micro_agents_are_selected_by_task_type():
    names = {agent.name for agent in select_micro_agents("security")}
    assert "security" in names


def test_optimizer_proposes_evidence_based_change():
    board = AgentScoreboard()
    for _ in range(5):
        board.record("coder", success=True, iterations=3, reviewer_rejected=True)
    suggestions = suggest_improvements(board)
    assert suggestions
    assert any("evidence" in item.proposed_change.lower() or "self-check" in item.proposed_change.lower() for item in suggestions)
