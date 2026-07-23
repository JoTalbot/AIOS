"""Config manager full tests."""
from aios_core.config_manager import ConfigManager
def test_config_defaults(): assert ConfigManager().stats() is not None
