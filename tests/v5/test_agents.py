from aios_core.v5.agents.registry import AgentRegistry


class DemoAgent:
    name = "demo"


def test_agent_registry():
    registry = AgentRegistry()
    registry.register(DemoAgent())
    assert registry.get("demo") is not None
