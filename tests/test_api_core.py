"""Tests for core API modules."""

from aios_core.api.app import AIOSApplication


def test_app_init():
    app = AIOSApplication()
    assert app is not None
