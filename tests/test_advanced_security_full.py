"""Full tests for advanced security module."""

from aios_core.advanced_security import AdvancedSecurity


def test_threat_detection():
    sec = AdvancedSecurity()
    assert sec.detect_threat({"ip": "0.0.0.0"}) is True
    assert sec.detect_threat({"ip": "192.168.1.1"}) is False


def test_encryption():
    sec = AdvancedSecurity()
    h = sec.encrypt_sensitive("hello")
    assert len(h) == 64  # SHA-256 hex


def test_api_key_generation():
    sec = AdvancedSecurity()
    key = sec.generate_api_key()
    assert len(key) > 10
