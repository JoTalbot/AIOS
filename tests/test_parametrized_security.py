"""Parametrized security tests."""
import pytest
from aios_core.advanced_security import AdvancedSecurity

@pytest.mark.parametrize("ip,is_threat", [
    ("0.0.0.0", True), ("127.0.0.1", True),
    ("192.168.1.1", False), ("10.0.0.1", False),
    ("8.8.8.8", False), ("1.1.1.1", False),
])
def test_ip_threat_detection(ip, is_threat):
    s = AdvancedSecurity()
    assert s.detect_threat({"ip": ip}) == is_threat
