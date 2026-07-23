"""Tests for config, config manager, and runtime config."""

from aios_core.config import AIOSConfig
from aios_core.config_manager import ConfigManager


def test_aios_config_init():
    cfg = AIOSConfig()
    assert cfg is not None


def test_config_manager_stats():
    cm = ConfigManager()
    s = cm.stats()
    assert isinstance(s, dict)
