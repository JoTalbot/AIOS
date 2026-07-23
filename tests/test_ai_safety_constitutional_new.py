"""Constitutional AI safety new."""
from aios_core.ai_safety_constitutional import ConstitutionalAI
def test(): s=ConstitutionalAI().stats(); assert isinstance(s,dict)
