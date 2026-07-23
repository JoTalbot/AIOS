"""V-test 2840."""
from aios_core.encryption import EncryptionService
from aios_core.rbac import RBACManager
from aios_core.zero_trust import ZeroTrustVerifier
from aios_core.privacy_guard import PrivacyGuard
from aios_core.differential_privacy import DifferentialPrivacy
from aios_core.security_jwt import JWTAuth

def test():
    es=EncryptionService()
    rm=RBACManager()
    zt=ZeroTrustVerifier()
    pg=PrivacyGuard()
    assert es.stats() is not None
    assert rm.stats() is not None
    assert zt.stats() is not None
    assert pg.stats() is not None
    assert DifferentialPrivacy() is not None
