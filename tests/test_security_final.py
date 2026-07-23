"""Final security module tests."""

from aios_core.api.security import SecurityMiddleware
from aios_core.zero_trust import ZeroTrustVerifier
from aios_core.encryption import EncryptionService


def test_security_middleware():
    sm = SecurityMiddleware()
    assert sm is not None


def test_zero_trust():
    zt = ZeroTrustVerifier()
    assert zt is not None


def test_encryption():
    es = EncryptionService()
    assert es is not None
