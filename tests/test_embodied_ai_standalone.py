"""embodied_ai test."""
from aios_core.embodied_ai import EmbodiedAgent
def test_init(): s = EmbodiedAgent().stats(); assert isinstance(s, dict)
