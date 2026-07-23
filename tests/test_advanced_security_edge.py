"""Advanced security edge."""
from aios_core.advanced_security import AdvancedSecurity
def test_hash(): h=AdvancedSecurity().encrypt_sensitive("test"); assert len(h)==64
def test_key(): k=AdvancedSecurity().generate_api_key(); assert len(k)>10
