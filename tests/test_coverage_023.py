"""Test honest AI."""
from aios_core.ai_safety_honest_ai import HonestAI
def test_honest(): assert HonestAI().stats() is not None
