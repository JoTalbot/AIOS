"""Viber messenger tests."""
from aios_core.modules.viber.messenger import ViberMessenger
def test_messenger_exists():
    assert ViberMessenger is not None
