"""Test multi-agent safety."""
from aios_core.ai_safety_multi_agent import MultiAgentSafety
def test_multiagent(): assert MultiAgentSafety().stats() is not None
