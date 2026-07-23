"""Integration: Security modules pipeline."""
from aios_core.encryption import EncryptionService
from aios_core.rbac import RBACManager
from aios_core.zero_trust import ZeroTrustVerifier
def test_security_pipeline():
    es = EncryptionService()
    rm = RBACManager()
    zt = ZeroTrustVerifier()
    assert es.stats() is not None
    assert rm.stats() is not None
    assert zt.stats() is not None
