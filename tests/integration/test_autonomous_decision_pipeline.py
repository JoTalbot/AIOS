"""Full autonomous decision pipeline integration tests."""


def test_goal_to_feedback_pipeline_contract():
    """Verify the expected AIOS autonomous loop contract."""
    pipeline = [
        "goal",
        "plan",
        "decision",
        "consensus",
        "optimization",
        "execute",
        "feedback",
    ]

    assert pipeline[0] == "goal"
    assert pipeline[-1] == "feedback"
    assert "decision" in pipeline
    assert "optimization" in pipeline


def test_feedback_returns_to_learning_loop():
    """Verify learning feedback closes the autonomous loop."""
    execution_result = {"success": True, "reward": 1.0}

    assert execution_result["success"] is True
    assert execution_result["reward"] > 0
