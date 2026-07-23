"""config_manager boundary test."""
from aios_core.config_manager import ConfigManager

def test(): assert ConfigManager().stats() is not None
