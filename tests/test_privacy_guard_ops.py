from aios_core.privacy_guard import PrivacyGuard
def test_ops():
    pg = PrivacyGuard()
    assert pg.stats() is not None