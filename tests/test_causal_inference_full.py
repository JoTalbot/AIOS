"""Causal inference full."""
from aios_core.causal_inference import CausalInference
def test_ci(): s=CausalInference().stats(); assert isinstance(s,dict)
