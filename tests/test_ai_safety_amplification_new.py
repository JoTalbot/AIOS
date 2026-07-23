"""AI safety amplification new."""
from aios_core.ai_safety_amplification import IteratedAmplification
def test(): s=IteratedAmplification().stats(); assert isinstance(s,dict)
