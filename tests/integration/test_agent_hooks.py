"""Agent hooks integration smoke test."""

from core.runtime.agent_hooks import AgentHooks


def test_agent_hooks_emit():
    hooks = AgentHooks()
    result = []
    hooks.register("start", lambda: result.append(True))
    hooks.emit("start")
    assert result == [True]
