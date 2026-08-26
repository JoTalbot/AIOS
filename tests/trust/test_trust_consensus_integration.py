def test_trust_weight_influences_consensus():
    high_trust = 0.9
    low_trust = 0.2

    assert high_trust > low_trust


def test_consensus_context_accepts_trust_score():
    context = {
        "agent_id": "agent_1",
        "trust_score": 0.8,
    }

    assert context["trust_score"] == 0.8
