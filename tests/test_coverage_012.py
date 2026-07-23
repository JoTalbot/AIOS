"""Test advanced red teaming."""
from aios_core.ai_safety_red_teaming_advanced import AdvancedRedTeam
def test_redteam(): assert AdvancedRedTeam().stats() is not None
