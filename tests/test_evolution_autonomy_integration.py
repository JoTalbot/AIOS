"""Integration tests for Evolution + Autonomy subsystems"""


from aios_core import Database, Orchestrator


def test_evolution_and_autonomy_integration():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    # Create proposal
    proposal = orch.evolution.propose(
        change={"type": "capability", "name": "new_skill"},
        component="capability_engine",
        reason="test integration",
    )
    assert proposal["id"] is not None
    assert proposal["status"] == "proposed"

    # Check stats
    evo_stats = orch.evolution.stats()
    assert evo_stats["total_proposals"] >= 1

    # Autonomy check
    autonomy = orch.autonomy.check_autonomy("test_agent", action_risk="high")
    assert "level" in autonomy
    assert "requires_approval" in autonomy

    # Record action
    orch.autonomy.record_action("test_agent", success=True)
    auto_stats = orch.autonomy.stats()
    assert "total_profiles" in auto_stats

    # Full stats from orchestrator
    stats = orch.stats()
    assert "evolution_proposals" in stats
    assert stats["evolution_proposals"] >= 1
