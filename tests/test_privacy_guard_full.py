"""Privacy guard full ops."""
from aios_core.privacy_guard import PrivacyGuard
def test_pg(): s=PrivacyGuard().stats(); assert isinstance(s,dict)
