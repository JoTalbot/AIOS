"""Swarm intelligence full."""
from aios_core.swarm_intelligence import SwarmOptimizer
def test(): s=SwarmOptimizer().stats(); assert isinstance(s,dict)
