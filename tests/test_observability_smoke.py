"""observability smoke test."""
def test_obs(): from aios_core.observability import ObservabilityStack; assert ObservabilityStack().stats() is not None
