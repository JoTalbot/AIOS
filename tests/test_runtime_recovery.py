"""Runtime recovery integration tests."""

from core.agents.manager import AgentManager


class DummyAgent:
    def __init__(self, name):
        self.name = name


def test_manager_snapshot_recovery():
    manager = AgentManager()
    manager.register(DummyAgent("agent"))

    snapshot = manager.snapshot()
    assert "agent" in snapshot

    restored = manager.recover(snapshot)
    assert restored["agent"] == snapshot["agent"]
