"""Tests for Instagram messenger and notifier."""

from aios_core.modules.instagram.messenger import InstagramMessenger
from aios_core.modules.instagram.bootstrap import InstagramBootstrap


def test_messenger_init():
    m = InstagramMessenger()
    assert m is not None


def test_bootstrap_init():
    b = InstagramBootstrap()
    assert b is not None
