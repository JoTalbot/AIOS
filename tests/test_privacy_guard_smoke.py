"""privacy_guard smoke test."""
def test_pg(): from aios_core.privacy_guard import PrivacyGuard; assert PrivacyGuard().stats() is not None
