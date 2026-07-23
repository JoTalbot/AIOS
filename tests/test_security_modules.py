"""Tests for security, privacy, and zero-trust modules."""

from aios_core.privacy_guard import PrivacyGuard
from aios_core.zero_trust import ZeroTrustVerifier
from aios_core.security_jwt import JWTAuth


def test_privacy_guard_stats():
    pg = PrivacyGuard()
    s = pg.stats()
    assert isinstance(s, dict)


def test_zero_trust_stats():
    zt = ZeroTrustVerifier()
    s = zt.stats()
    assert isinstance(s, dict)


def test_jwt_auth_stats():
    jwt = JWTAuth(secret="test-secret-key-for-unit-testing")
    assert jwt is not None
