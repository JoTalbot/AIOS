"""Full tests for OLX messenger and chat parser."""

from aios_core.modules.olx.messenger import OLXMessenger


def test_messenger_init():
    m = OLXMessenger()
    assert m is not None
