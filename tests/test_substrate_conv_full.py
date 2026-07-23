"""Substrate convergence full."""
from aios_core.substrate_convergence import SubstrateConvergence
def test(): s=SubstrateConvergence().stats(); assert isinstance(s,dict)
