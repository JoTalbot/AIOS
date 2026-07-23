"""embodied_ai test."""
def test(): from aios_core.embodied_ai import EmbodiedAgent; s = EmbodiedAgent().stats(); assert isinstance(s, dict)
