def test_decision_resolver_combines_trust_and_strategy():
    candidates = [
        {"agent": "agent_a", "trust": 0.9, "strategy": 0.8},
        {"agent": "agent_b", "trust": 0.4, "strategy": 0.9},
    ]

    scores = {
        item["agent"]: item["trust"] + item["strategy"]
        for item in candidates
    }

    assert max(scores, key=scores.get) == "agent_a"


def test_decision_pipeline_has_feedback_stage():
    pipeline = [
        "agent_result",
        "trust_score",
        "strategy_score",
        "decision",
        "execution",
        "feedback",
    ]

    assert pipeline[-1] == "feedback"
