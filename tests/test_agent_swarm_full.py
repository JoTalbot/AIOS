"""Full tests for agent swarm module."""

from aios_core.agent_architecture import AdvancedAgent
from aios_core.agent_swarm import AgentSwarm


def test_broadcast_reaches_all():
    swarm = AgentSwarm("test")
    a1 = AdvancedAgent("a1")
    a2 = AdvancedAgent("a2")
    swarm.add_agent(a1)
    swarm.add_agent(a2)
    swarm.broadcast({"cmd": "ping"})
    assert len(a1.memory.short_term) == 1
    assert len(a2.memory.short_term) == 1


def test_collective_decision_vote_count():
    swarm = AgentSwarm("vote")
    for i in range(5):
        swarm.add_agent(AdvancedAgent(f"v{i}"))
    result = swarm.collective_decision("topic_x")
    assert result["votes"] == 5
    assert result["decision"] == "approved"
