"""Test constitutional AI safety."""
from aios_core.ai_safety_constitutional import ConstitutionalAI
def test_constitutional(): assert ConstitutionalAI().stats() is not None
