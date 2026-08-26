from core.optimization.policy_optimizer import PolicyOptimizer


def test_policy_optimizer_improves_score():
    optimizer = PolicyOptimizer()

    result = optimizer.optimize(
        action="retry",
        previous_score=0.5,
    )

    assert result.action == "retry"
    assert result.new_score >= result.previous_score


def test_policy_optimizer_keeps_action():
    optimizer = PolicyOptimizer()

    result = optimizer.optimize(
        action="restore",
        previous_score=0.8,
    )

    assert result.action == "restore"
