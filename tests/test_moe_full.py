"""MoE full ops."""
from aios_core.moe import MixtureOfExperts
def test(): s=MixtureOfExperts().stats(); assert isinstance(s,dict)
