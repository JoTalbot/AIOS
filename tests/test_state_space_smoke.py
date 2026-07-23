"""state_space smoke test."""
def test_ssm(): from aios_core.state_space import StateSpaceModel; assert StateSpaceModel().stats() is not None
