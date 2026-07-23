"""Tests for Agent Swarm."""

from aios_core.agent_architecture import AdvancedAgent
from aios_core.agent_swarm import AgentSwarm


def test_swarm_add_agent():
    swarm = AgentSwarm("test_swarm")
    agent = AdvancedAgent("worker1")
    swarm.add_agent(agent)
    assert swarm.stats()["agents"] == 1


def test_swarm_broadcast():
    swarm = AgentSwarm("broadcast_test")
    a1 = AdvancedAgent("a1")
    a2 = AdvancedAgent("a2")
    swarm.add_agent(a1)
    swarm.add_agent(a2)
    swarm.broadcast({"msg": "hello"})
    assert len(a1.memory.short_term) == 1
    assert len(a2.memory.short_term) == 1
    assert a1.memory.short_term[0]["msg"] == "hello"


def test_swarm_collective_decision():
    swarm = AgentSwarm("decision_test")
    swarm.add_agent(AdvancedAgent("voter1"))
    swarm.add_agent(AdvancedAgent("voter2"))
    result = swarm.collective_decision("deploy")
    assert result["decision"] == "approved"
    assert result["votes"] == 2


def test_swarm_stats_initial():
    swarm = AgentSwarm("empty")
    assert swarm.stats() == {"agents": 0, "shared_memory": 0}
