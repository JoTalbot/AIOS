from core.trust.multi_agent_trust_learning import MultiAgentTrustLearning


def test_agent_trust_updates():
    trust = MultiAgentTrustLearning()
    trust.register_agent("agent_a")
    trust.update_trust("agent_a", 1.0)

    assert trust.get_trust("agent_a") > 0


def test_unknown_agent_safe_fallback():
    trust = MultiAgentTrustLearning()

    assert trust.get_trust("unknown") == 0
