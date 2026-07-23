"""Global swarm full."""
from aios_core.global_swarm import GlobalSwarm
def test(): s=GlobalSwarm().stats(); assert isinstance(s,dict)
