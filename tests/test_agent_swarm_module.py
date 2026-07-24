"""Tests for aios_core/agent_swarm.py"""
from __future__ import annotations
import pytest
from aios_core.agent_swarm import AgentSwarm, SwarmAgent


@pytest.fixture()
def swarm():
    return AgentSwarm(name="test_swarm")


def make_agent(agent_id: str, caps: list[str] | None = None):
    return SwarmAgent(id=agent_id, capabilities=caps or [])


class TestAgentSwarm:
    def test_create(self, swarm):
        assert swarm is not None
        assert swarm.name == "test_swarm"

    def test_add_agent(self, swarm):
        swarm.add_agent(make_agent("a1", ["scrape", "analyze"]))

    def test_get_agent(self, swarm):
        swarm.add_agent(make_agent("a1", ["test"]))
        agent = swarm.get_agent("a1")
        assert agent is not None
        assert agent.id == "a1"

    def test_remove_agent(self, swarm):
        swarm.add_agent(make_agent("a1"))
        swarm.remove_agent("a1")

    def test_send_message(self, swarm):
        swarm.add_agent(make_agent("a1"))
        swarm.add_agent(make_agent("a2"))
        swarm.send_message(from_id="a1", to_id="a2", content="hello")

    def test_broadcast(self, swarm):
        swarm.add_agent(make_agent("a1"))
        swarm.broadcast(message="broadcast msg")

    def test_assign_task(self, swarm):
        swarm.add_agent(make_agent("a1", ["scrape"]))
        result = swarm.assign_task(task_name="scrape_olx", required_capability="scrape")
        assert result is not None

    def test_stats(self, swarm):
        swarm.add_agent(make_agent("a1"))
        s = swarm.stats()
        assert isinstance(s, dict)
