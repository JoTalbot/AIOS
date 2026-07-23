"""Test debate protocol full."""
from aios_core.ai_safety_debate import DebateProtocol
def test_debate(): assert DebateProtocol().stats() is not None
