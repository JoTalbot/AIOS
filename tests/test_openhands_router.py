from aios_core.openhands import AdaptiveRouter, AgentRole, AgentScoreboard, default_route_candidates


def test_router_prefers_proven_candidate():
    board = AgentScoreboard()
    for _ in range(5):
        board.record(AgentRole.CODER.value, success=True)
    for _ in range(5):
        board.record(AgentRole.REVIEWER.value, success=False)
    decision = AdaptiveRouter(board).choose((AgentRole.CODER, AgentRole.REVIEWER))
    assert decision.role is AgentRole.CODER
    assert decision.score > 0


def test_router_is_deterministic_without_history():
    decision = AdaptiveRouter(AgentScoreboard()).choose((AgentRole.CODER, AgentRole.REVIEWER))
    assert decision.role is AgentRole.CODER


def test_default_candidates_are_task_specific():
    assert default_route_candidates("security") == (AgentRole.SECURITY, AgentRole.REVIEWER)
    assert default_route_candidates("bugfix") == (AgentRole.TESTER, AgentRole.CODER)
