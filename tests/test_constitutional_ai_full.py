"""Tests for constitutional AI and debate protocol."""

from aios_core.ai_safety_constitutional import ConstitutionalAI
from aios_core.ai_safety_debate import DebateProtocol


def test_constitutional_ai_init():
    cai = ConstitutionalAI()
    assert cai is not None


def test_debate_protocol_full():
    dp = DebateProtocol()
    assert dp is not None
    s = dp.stats()
    assert isinstance(s, dict)
