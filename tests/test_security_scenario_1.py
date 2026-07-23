"""Security scenario test."""
from aios_core.secret_manager import SecretManager
from aios_core.advanced_security import AdvancedSecurity

def test_keys():
    s1 = AdvancedSecurity()
    k1 = s1.generate_api_key()
    k2 = s1.generate_api_key()
    assert k1 != k2
    assert len(k1) > 10

def test_secret():
    assert SecretManager() is not None
