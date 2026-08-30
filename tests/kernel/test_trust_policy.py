from aios_core.kernel.trust import TrustManager
from aios_core.kernel.policies import PolicyEngine


def test_trust_default_is_unknown():
    manager = TrustManager()
    assert manager.evaluate("agent-001") == "T0"


def test_policy_denies_unknown_capability():
    policy = PolicyEngine()
    result = policy.evaluate("execute_tool")
    assert result.allowed is False
