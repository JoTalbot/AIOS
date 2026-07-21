"""Advanced Autonomy Manager v3.0 tests (auto-adjustment)"""

import pytest
from aios_core import Orchestrator, Database
from aios_core.autonomy_manager import AutonomyLevel


def test_automatic_promotion():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    agent_id = "agent_promote_test"

    # Grant initial autonomy
    orch.autonomy.grant_autonomy(agent_id, level=2)

    # Simulate high success rate
    for _ in range(55):
        orch.autonomy.record_action(agent_id, success=True)

    profile = orch.autonomy.get_profile(agent_id)
    assert profile is not None
    assert profile["level"] >= 3  # Should have been promoted automatically


def test_automatic_demotion():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    agent_id = "agent_demote_test"

    # Grant high autonomy
    orch.autonomy.grant_autonomy(agent_id, level=4)

    # Simulate poor performance
    for i in range(25):
        success = i > 8  # only 8 successes out of 25
        orch.autonomy.record_action(agent_id, success=success)

    profile = orch.autonomy.get_profile(agent_id)
    assert profile is not None
    assert profile["level"] <= 2  # Should have been demoted


def test_stats_includes_auto_adjusted():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    agent_id = "stats_test_agent"
    orch.autonomy.grant_autonomy(agent_id, level=1)

    for _ in range(55):
        orch.autonomy.record_action(agent_id, success=True)

    stats = orch.autonomy.stats()
    assert "auto_adjusted_count" in stats
    assert stats["auto_adjusted_count"] >= 1