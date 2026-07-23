"""Test advanced interpretability."""
from aios_core.ai_safety_interpretability_advanced import AdvancedInterpretability
def test_adv_interp(): assert AdvancedInterpretability().stats() is not None
