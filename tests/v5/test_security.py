from aios_core.v5.security.policy import PolicyEngine


def test_policy_rule():
    policy = PolicyEngine()
    policy.set_rule("agent", "read", True)
    assert policy.allow("read", "agent")
