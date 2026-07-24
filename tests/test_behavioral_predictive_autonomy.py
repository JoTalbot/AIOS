import pytest
from aios_core.predictive_autonomy import PredictiveAutonomyRegulator
from aios_core.autonomy_manager import AutonomyLevel

def test_autonomy_low_risk_action():
    regulator = PredictiveAutonomyRegulator()
    plan_step = {"action": "read_data", "complexity": 2.0}
    
    level, reason = regulator.regulate_autonomy(
        agent_id="agent_1",
        current_level=AutonomyLevel.LEVEL_4_AUTONOMOUS,
        plan_step=plan_step,
        agent_history_stats={"failure_rate": 0.05}
    )
    
    assert level == AutonomyLevel.LEVEL_4_AUTONOMOUS
    assert "Risk evaluated" in reason
    assert regulator.stats()["total_regulations"] == 1

def test_autonomy_high_risk_action_clamp():
    regulator = PredictiveAutonomyRegulator(high_risk_threshold=0.6)
    # "delete" adds 0.5 risk, complexity > 5 adds 0.2 -> total 0.8
    plan_step = {"action": "delete_all_users", "complexity": 8.0}
    
    level, reason = regulator.regulate_autonomy(
        agent_id="agent_2",
        current_level=AutonomyLevel.LEVEL_4_AUTONOMOUS,
        plan_step=plan_step,
        agent_history_stats={"failure_rate": 0.1}
    )
    
    assert level == AutonomyLevel.LEVEL_2_SUPERVISED
    assert "clamped to Level 2" in reason
    assert regulator.stats()["clamped_count"] == 1

def test_autonomy_critical_risk_action_downgrade():
    regulator = PredictiveAutonomyRegulator(critical_risk_threshold=0.85)
    # "wipe" adds 0.5 risk, complexity 10 adds 0.2, high failure rate 0.9 adds 0.27 -> total 0.97
    plan_step = {"action": "wipe_production_db", "complexity": 10.0}
    
    level, reason = regulator.regulate_autonomy(
        agent_id="agent_3",
        current_level=AutonomyLevel.LEVEL_5_SELF_DIRECTED,
        plan_step=plan_step,
        agent_history_stats={"failure_rate": 0.9}
    )
    
    assert level == AutonomyLevel.LEVEL_1_ASSISTED
    assert "Critical Risk" in reason
    assert regulator.stats()["total_regulations"] == 1
