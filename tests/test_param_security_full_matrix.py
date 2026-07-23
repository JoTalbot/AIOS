"""Parametrized: security full."""
import pytest
from aios_core.advanced_security import AdvancedSecurity

@pytest.mark.parametrize("ip", [
    "0.0.0.0","127.0.0.1","192.168.1.1","10.0.0.1",
    "172.16.0.1","8.8.8.8","1.1.1.1","255.255.255.255",
])
def test_ip_detection(ip):
    s = AdvancedSecurity()
    result = s.detect_threat({"ip": ip})
    assert isinstance(result, bool)

@pytest.mark.parametrize("data", ["","a","hello","long_string"*10])
def test_hash_properties(data):
    s = AdvancedSecurity()
    h = s.encrypt_sensitive(data)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
