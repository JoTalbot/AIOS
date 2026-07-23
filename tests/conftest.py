"""AIOS test configuration."""

import pytest

# Enable pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """Set asyncio mode to auto for async test support."""
    # pytest-asyncio auto mode: async tests/fixtures are auto-detected
    if hasattr(config.option, "asyncio_mode"):
        config.option.asyncio_mode = "auto"

# pytest markers for test categorization
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with -k 'not slow')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "real_device: marks tests requiring a real Android device")
