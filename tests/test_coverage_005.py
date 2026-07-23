"""Test safety governance."""
from aios_core.ai_safety_governance_advanced import AdvancedAIGovernance
def test_governance(): assert AdvancedAIGovernance().stats() is not None
