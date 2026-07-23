"""Viber operations tests."""
from aios_core.modules.viber.bootstrap import ViberBootstrap
from aios_core.modules.viber.messenger import ViberMessenger
def test_viber_tools():
    assert ViberBootstrap is not None
