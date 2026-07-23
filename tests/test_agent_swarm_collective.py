from aios_core.agent_architecture import AdvancedAgent
from aios_core.agent_swarm import AgentSwarm
def test_swarm():
    s = AgentSwarm('t')
    s.add_agent(AdvancedAgent('a1'))
    s.add_agent(AdvancedAgent('a2'))
    r = s.collective_decision('vote')
    assert r['votes'] == 2