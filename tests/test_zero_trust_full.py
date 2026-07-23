"""Zero trust full ops."""
from aios_core.zero_trust import ZeroTrustVerifier
def test_zt(): s=ZeroTrustVerifier().stats(); assert isinstance(s,dict)
