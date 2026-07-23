"""swarm_intelligence test."""
def test(): from aios_core.swarm_intelligence import SwarmOptimizer; s = SwarmOptimizer().stats(); assert isinstance(s, dict)
