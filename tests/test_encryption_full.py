"""Full tests for encryption service."""

from aios_core.encryption import EncryptionService


def test_encryption_init():
    es = EncryptionService()
    assert es is not None


def test_encryption_stats():
    es = EncryptionService()
    s = es.stats()
    assert isinstance(s, dict)
