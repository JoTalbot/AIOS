"""causal_inference smoke test."""
def test_ci(): from aios_core.causal_inference import CausalInference; assert CausalInference().stats() is not None
