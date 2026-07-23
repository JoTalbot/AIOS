"""Tests for bootstrap, setup, and tools."""

from aios_core.modules.olx.bootstrap import OLXBootstrap
from aios_core.platforms.onboard import Onboarder


def test_olx_bootstrap_init():
    b = OLXBootstrap()
    assert b is not None


def test_onboarder_init():
    o = Onboarder()
    assert o is not None
