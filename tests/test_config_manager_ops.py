"""Config manager ops."""
from aios_core.config_manager import ConfigManager
def test_cm(): s = ConfigManager().stats(); assert isinstance(s, dict)
