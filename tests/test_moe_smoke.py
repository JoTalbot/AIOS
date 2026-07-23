"""moe smoke test."""
def test_moe(): from aios_core.moe import MixtureOfExperts; assert MixtureOfExperts().stats() is not None
