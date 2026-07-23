"""ai_scientist test."""
def test(): from aios_core.ai_scientist import AIScientist; s = AIScientist().stats(); assert isinstance(s, dict)
