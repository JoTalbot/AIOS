"""Multi-agent RL full."""
from aios_core.multi_agent_rl import MultiAgentRL
def test(): s=MultiAgentRL().stats(); assert isinstance(s,dict)
