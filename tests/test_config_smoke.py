"""config smoke test."""
def test_cfg(): from aios_core.config import AIOSConfig; assert AIOSConfig() is not None
