"""Encryption full ops."""
from aios_core.encryption import EncryptionService
def test_enc(): s=EncryptionService().stats(); assert isinstance(s,dict)
