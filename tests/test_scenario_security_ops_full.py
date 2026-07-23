"""Security ops full scenario."""
from aios_core.encryption import EncryptionService
from aios_core.rbac import RBACManager
from aios_core.zero_trust import ZeroTrustVerifier
from aios_core.privacy_guard import PrivacyGuard
from aios_core.differential_privacy import DifferentialPrivacy
def test_security_ops():
    for o in [EncryptionService(), RBACManager(), ZeroTrustVerifier(),
              PrivacyGuard()]:
        assert o.stats() is not None
    assert DifferentialPrivacy() is not None
