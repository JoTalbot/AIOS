"""swarm_intelligence standalone test."""
from aios_core.swarm_intelligence import SwarmOptimizer
def test_init(): s = SwarmOptimizer().stats(); assert isinstance(s, dict)
