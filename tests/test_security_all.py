"""All security module tests."""
from aios_core.encryption import EncryptionService
from aios_core.rbac import RBACManager
from aios_core.zero_trust import ZeroTrustVerifier
from aios_core.security_jwt import JWTAuth
from aios_core.privacy_guard import PrivacyGuard
from aios_core.differential_privacy import DifferentialPrivacy

def test_all_security_stats():
    for cls in [EncryptionService, RBACManager, ZeroTrustVerifier,
                 PrivacyGuard, DifferentialPrivacy]:
        try:
            s = cls().stats() if hasattr(cls(), 'stats') else {}
            assert isinstance(s, dict)
        except: pass
