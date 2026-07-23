from aios_core.zero_trust import ZeroTrustVerifier
def test_verify():
    zt = ZeroTrustVerifier()
    assert zt.stats() is not None