import pytest
from aios_core.advanced_security import AdvancedSecurity

@pytest.mark.parametrize("ip,threat", [
    ("0.0.0.0", True), ("127.0.0.1", True), ("192.168.1.1", False),
    ("10.0.0.1", False), ("172.16.0.1", False), ("8.8.8.8", False),
])
def test_ip_threat(ip, threat):
    assert AdvancedSecurity().detect_threat({"ip": ip}) == threat

@pytest.mark.parametrize("data", ["hello", "test", "password123", ""])
def test_encrypt_sensitive(data):
    h = AdvancedSecurity().encrypt_sensitive(data)
    assert len(h) == 64
