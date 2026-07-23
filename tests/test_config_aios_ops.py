"""AIOS config ops."""
from aios_core.config import AIOSConfig, DatabaseConfig, LoggingConfig
def test_db_cfg(): d=DatabaseConfig(path="x.db"); assert d.path=="x.db"
def test_log_cfg(): l=LoggingConfig(level="DEBUG"); assert l.level=="DEBUG"
