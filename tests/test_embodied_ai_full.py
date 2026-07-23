"""Embodied AI full."""
from aios_core.embodied_ai import EmbodiedAgent
def test(): s=EmbodiedAgent().stats(); assert isinstance(s,dict)
