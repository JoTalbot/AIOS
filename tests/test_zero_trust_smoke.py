"""zero_trust smoke test."""
def test_zt(): from aios_core.zero_trust import ZeroTrustVerifier; assert ZeroTrustVerifier().stats() is not None
