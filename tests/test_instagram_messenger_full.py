"""Instagram messenger full tests."""
from aios_core.modules.instagram.messenger import InstagramMessenger
def test_messenger_ops():
    m = InstagramMessenger()
    assert m is not None
