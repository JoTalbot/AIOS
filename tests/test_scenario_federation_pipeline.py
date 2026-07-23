"""Federation + multi-agent pipeline."""
from aios_core.federation_manager import FederationManager
from aios_core.multi_agent_orchestrator import MultiAgentOrchestrator
from aios_core.agent_swarm import AgentSwarm
from aios_core.agent_architecture import AdvancedAgent

def test_federation_flow():
    fm = FederationManager()
    mo = MultiAgentOrchestrator()
    swarm = AgentSwarm("test_swarm")
    agent = AdvancedAgent("worker")
    swarm.add_agent(agent)
    assert fm.stats() is not None
    assert mo.stats() is not None
    assert swarm.stats()["agents"] == 1
