from aios_core.causal_inference import CausalInference
def test_ops():
    ci = CausalInference()
    assert ci.stats() is not None