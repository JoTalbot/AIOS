"""Security pipeline scenario."""
from aios_core.encryption import EncryptionService
from aios_core.advanced_security import AdvancedSecurity
from aios_core.zero_trust import ZeroTrustVerifier

def test_security_layers():
    es = EncryptionService()
    sec = AdvancedSecurity()
    zt = ZeroTrustVerifier()
    assert es.stats() is not None
    assert sec.detect_threat({"ip": "8.8.8.8"}) is False
    assert zt.stats() is not None
    key = sec.generate_api_key()
    assert len(key) > 10
    hashed = sec.encrypt_sensitive(key)
    assert len(hashed) == 64
