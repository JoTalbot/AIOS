"""Prom bootstrap tests."""
from aios_core.modules.prom.bootstrap import PromBootstrap
def test_bootstrap_exists():
    assert PromBootstrap is not None
