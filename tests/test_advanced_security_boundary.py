"""advanced_security boundary test."""
from aios_core.advanced_security import AdvancedSecurity

def test_threat_safe(): assert AdvancedSecurity().detect_threat({"ip":"8.8.8.8"}) is False
