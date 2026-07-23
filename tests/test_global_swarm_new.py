"""global_swarm test."""
def test(): from aios_core.global_swarm import GlobalSwarm; s = GlobalSwarm().stats(); assert isinstance(s, dict)
