"""Tests for centralised YAML config."""
import os
import tempfile
from pathlib import Path

import yaml

from aios_core.config_central import (
    AIOSConfig,
    generate_default_config,
    load_config,
)


def test_default_config():
    cfg = AIOSConfig()
    assert cfg.database.path == "aios.sqlite"
    assert cfg.backup.retention_days == 30
    assert cfg.logging.level == "INFO"
    assert cfg.pacing.actions_per_hour == 60


def test_load_config_defaults():
    cfg = load_config()
    assert cfg.database.path == "aios.sqlite"
    assert cfg.backup.directory == "./backups"


def test_env_override():
    os.environ["AIOS_DB_PATH"] = "/tmp/test_override.db"
    cfg = load_config()
    assert cfg.database.path == "/tmp/test_override.db"
    del os.environ["AIOS_DB_PATH"]


def test_yaml_file_load():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"database": {"path": "/yaml/db.sqlite"}, "logging": {"level": "DEBUG"}}, f)
        tmp = f.name
    try:
        cfg = load_config(tmp)
        assert cfg.database.path == "/yaml/db.sqlite"
        assert cfg.logging.level == "DEBUG"
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_env_beats_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"database": {"path": "/yaml/db.sqlite"}}, f)
        tmp = f.name
    os.environ["AIOS_DB_PATH"] = "/env/db.sqlite"
    try:
        cfg = load_config(tmp)
        assert cfg.database.path == "/env/db.sqlite"
    finally:
        Path(tmp).unlink(missing_ok=True)
        del os.environ["AIOS_DB_PATH"]


def test_generate_default_config():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        tmp = f.name
    try:
        text = generate_default_config(tmp)
        assert "database:" in text
        assert "backup:" in text
        assert Path(tmp).exists()
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_all_sections_present():
    cfg = AIOSConfig()
    for attr in ("database", "backup", "audit", "constitution", "policies",
                 "logging", "pacing", "webhook", "platforms"):
        assert hasattr(cfg, attr), f"Missing section: {attr}"
