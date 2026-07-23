"""Cosmic swarm full."""
from aios_core.cosmic_swarm_matrix import CosmicSwarmMatrix
def test(): s=CosmicSwarmMatrix().stats(); assert isinstance(s,dict)
