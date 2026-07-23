"""Hierarchical RL full."""
from aios_core.hierarchical_rl import HierarchicalRL
def test(): s=HierarchicalRL().stats(); assert isinstance(s,dict)
