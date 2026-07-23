"""ai_alignment test."""
def test(): from aios_core.ai_alignment import AIAlignment; s = AIAlignment().stats(); assert isinstance(s, dict)
