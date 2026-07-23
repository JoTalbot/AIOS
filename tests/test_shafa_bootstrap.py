"""Shafa bootstrap tests."""
from aios_core.modules.shafa.bootstrap import ShafaBootstrap
def test_bootstrap_exists():
    assert ShafaBootstrap is not None
