"""AIOS test configuration."""

import pytest


def pytest_configure(config):
    """Set asyncio mode to auto for async test support."""
    # pytest-asyncio auto mode: async tests/fixtures are auto-detected
    if hasattr(config.option, 'asyncio_mode'):
        config.option.asyncio_mode = "auto"