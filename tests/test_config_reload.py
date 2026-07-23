from aios_core.config_manager import ConfigManager
def test_reload():
    cm = ConfigManager()
    assert cm.stats() is not None