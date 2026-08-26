"""State persistence tests."""

from core.runtime.state_store import AgentStateStore


def test_agent_state_migration():
    store = AgentStateStore()
    store.save_agent_state("agent-1", {"value": 1}, version=1)

    result = store.migrate(
        "agent-1",
        2,
        lambda state, old, new: {**state, "migrated": True},
    )

    assert result["migrated"] is True
    assert store.version("agent-1") == 2


def test_agent_state_restore_copy():
    store = AgentStateStore()
    store.save_agent_state("agent-1", {"items": []})

    state = store.load_agent_state("agent-1")
    state["items"].append(1)

    assert store.load_agent_state("agent-1")["items"] == [1]
