"""Test causal interpretability."""
from aios_core.ai_safety_causal_interpretability import CausalInterpretability
def test_causal(): assert CausalInterpretability().stats() is not None
