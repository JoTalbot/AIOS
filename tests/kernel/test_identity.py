from aios_core.kernel import AgentIdentity


def test_agent_capability():
    agent = AgentIdentity("agent-001", "developer", ["code"])
    assert agent.has_capability("code")
