"""Tests for AIOS Configuration module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from aios_core.config import Config, DatabaseConfig, LoggingConfig


def test_config_loads_from_yaml():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump({"database": {"path": "/tmp/test.db"}}, f)
        tmp = f.name

    try:
        cfg = Config(config_path=tmp)
        assert cfg.database.path == "/tmp/test.db"
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_config_defaults_when_no_file():
    cfg = Config(project_root="/nonexistent")
    # Falls back to built-in defaults
    assert cfg.logging.level == "INFO"
    assert cfg.database.path == "aios.db"


def test_database_config_dataclass():
    db = DatabaseConfig(path="mydb.sqlite")
    assert db.path == "mydb.sqlite"


def test_logging_config_dataclass():
    log = LoggingConfig(level="DEBUG", format="%(message)s")
    assert log.level == "DEBUG"
    assert log.format == "%(message)s"
