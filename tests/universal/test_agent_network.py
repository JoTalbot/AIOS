def test_agent_registry_foundation():
    from universal.agents.agent_registry import AgentRegistry

    registry = AgentRegistry()
    registry.register("agent", object())

    assert registry.get("agent") is not None
