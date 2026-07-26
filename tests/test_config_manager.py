"""Tests for aios_core/config.py and aios_core/config_manager.py."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from aios_core.config import (
    AIOSConfig,
    DatabaseConfig,
    LoggingConfig,
    load_config,
)
from aios_core.config_manager import ConfigLayer, ConfigManager


# ── config.py tests ──────────────────────────────────────────────────────


class TestAIOSConfigFromDict:
    def test_from_dict_uses_defaults_for_missing_sections(self):
        cfg = AIOSConfig.from_dict({})
        assert cfg.database.path == "aios.db"
        assert cfg.audit.retention_days == 90
        assert cfg.approval.timeout_seconds == 86400
        assert cfg.logging.level == "INFO"

    def test_from_dict_overrides_defaults(self):
        cfg = AIOSConfig.from_dict(
            {
                "database": {"path": "/custom/db.sqlite"},
                "logging": {"level": "DEBUG"},
            }
        )
        assert cfg.database.path == "/custom/db.sqlite"
        assert cfg.logging.level == "DEBUG"

    def test_from_dict_coerces_int_fields(self):
        cfg = AIOSConfig.from_dict(
            {"audit": {"retention_days": "180"}, "approval": {"timeout_seconds": "3600"}}
        )
        assert cfg.audit.retention_days == 180
        assert cfg.approval.timeout_seconds == 3600

    def test_from_dict_preserves_project_root(self):
        cfg = AIOSConfig.from_dict({}, project_root="/my/project")
        assert cfg.project_root == "/my/project"

    def test_from_dict_nested_partial_override(self):
        cfg = AIOSConfig.from_dict({"logging": {"level": "WARNING"}})
        assert cfg.logging.level == "WARNING"
        assert cfg.logging.format == LoggingConfig.format


class TestAIOSConfigResolvePath:
    def test_resolve_absolute_path_unchanged(self):
        cfg = AIOSConfig(project_root="/project")
        assert cfg.resolve_path("/absolute/path") == "/absolute/path"

    def test_resolve_relative_with_project_root(self):
        cfg = AIOSConfig(project_root="/project")
        assert cfg.resolve_path("subdir/file.txt") == "/project/subdir/file.txt"

    def test_resolve_relative_without_project_root(self):
        cfg = AIOSConfig(project_root="")
        assert cfg.resolve_path("subdir/file.txt") == "subdir/file.txt"


class TestLoadConfig:
    def test_load_config_returns_aios_config(self, tmp_path):
        config_file = tmp_path / "aios_config.yaml"
        config_file.write_text("database:\n  path: /tmp/test.db\n")
        cfg = load_config(str(config_file))
        assert isinstance(cfg, AIOSConfig)
        assert cfg.database.path == "/tmp/test.db"

    def test_load_config_env_overrides_yaml(self, tmp_path, monkeypatch):
        config_file = tmp_path / "aios_config.yaml"
        config_file.write_text("database:\n  path: /yaml/db.sqlite\n")
        monkeypatch.setenv("AIOS_DB_PATH", "/env/db.sqlite")
        cfg = load_config(str(config_file))
        assert cfg.database.path == "/env/db.sqlite"

    def test_load_config_missing_file_uses_defaults(self, tmp_path):
        cfg = load_config(str(tmp_path / "nonexistent.yaml"))
        assert cfg.database.path == "aios.db"
        assert cfg.audit.file_path == "audit_log.jsonl"

    def test_load_config_json_file(self, tmp_path):
        config_file = tmp_path / "aios_config.json"
        config_file.write_text(json.dumps({"database": {"path": "/json/db.sqlite"}}))
        cfg = load_config(str(config_file))
        assert cfg.database.path == "/json/db.sqlite"

    def test_load_config_yaml_precedence_over_defaults(self, tmp_path):
        config_file = tmp_path / "aios_config.yaml"
        config_file.write_text("audit:\n  retention_days: 30\n")
        cfg = load_config(str(config_file))
        assert cfg.audit.retention_days == 30


# ── config_manager.py tests ──────────────────────────────────────────────


class TestConfigManagerLoad:
    def test_load_creates_layers(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/managed.db\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        assert len(mgr.layers) == 3
        assert mgr.config["database"]["path"] == "/tmp/managed.db"

    def test_load_missing_file_uses_defaults(self, tmp_path):
        mgr = ConfigManager(str(tmp_path / "missing.yaml"))
        mgr.load()
        assert mgr.config == {}
        assert len(mgr.layers) == 3

    def test_load_env_flat_key_loading(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /file/db.sqlite\n")
        monkeypatch.setenv("AIOS_DB_PATH", "/env/db.sqlite")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        assert mgr.config["db_path"] == "/env/db.sqlite"

    def test_load_yaml_file_parsing(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "audit:\n  file_path: /tmp/audit.jsonl\n  retention_days: 30\n"
        )
        mgr = ConfigManager(str(config_file))
        mgr.load()
        assert mgr.config["audit"]["file_path"] == "/tmp/audit.jsonl"
        assert mgr.config["audit"]["retention_days"] == 30


class TestConfigManagerAccess:
    def test_get_existing_key(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        assert mgr.get("database") == {"path": "/tmp/db.sqlite"}

    def test_get_missing_key_returns_default(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        assert mgr.get("nonexistent", "fallback") == "fallback"

    def test_get_nested_dot_notation(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        assert mgr.get_nested("database.path") == "/tmp/db.sqlite"
        assert mgr.get_nested("database.missing", "default") == "default"
        assert mgr.get_nested("nonexistent.key", "fallback") == "fallback"

    def test_set_creates_override_layer(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        mgr.set("top_level_key", "override_value")
        assert mgr.get("top_level_key") == "override_value"


class TestConfigManagerLayers:
    def test_layer_priority_ordering(self, tmp_path):
        mgr = ConfigManager(str(tmp_path / "config.yaml"))
        mgr.load()
        priorities = [layer.priority for layer in mgr.layers]
        assert priorities == sorted(priorities, reverse=True)

    def test_add_override_layer(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        mgr.add_override({"database": {"path": "/override/db.sqlite"}})
        assert mgr.get_nested("database.path") == "/override/db.sqlite"

    def test_add_override_with_custom_priority(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        mgr.add_override({"logging": {"level": "DEBUG"}}, priority=5)
        assert mgr.get_nested("logging.level") == "DEBUG"


class TestConfigManagerSchemaValidation:
    def test_validate_passes_with_correct_types(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        mgr.set_schema({"database": dict})
        result = mgr.validate()
        assert result["valid"] is True
        assert result["errors"] == {}

    def test_validate_fails_with_wrong_type(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        mgr.set_schema({"database": str})
        result = mgr.validate()
        assert result["valid"] is False
        assert "database" in result["errors"]

    def test_validate_ignores_none_values(self, tmp_path):
        mgr = ConfigManager(str(tmp_path / "config.yaml"))
        mgr.load()
        mgr.set_schema({"nonexistent_key": str})
        result = mgr.validate()
        assert result["valid"] is True


class TestConfigManagerCoercion:
    def test_coerce_value_to_bool_true(self):
        mgr = ConfigManager()
        assert mgr._coerce_value("true") is True
        assert mgr._coerce_value("yes") is True
        assert mgr._coerce_value("1") is True

    def test_coerce_value_to_bool_false(self):
        mgr = ConfigManager()
        assert mgr._coerce_value("false") is False
        assert mgr._coerce_value("no") is False
        assert mgr._coerce_value("0") is False

    def test_coerce_value_to_int(self):
        mgr = ConfigManager()
        assert mgr._coerce_value("42") == 42
        assert isinstance(mgr._coerce_value("42"), int)

    def test_coerce_value_to_float(self):
        mgr = ConfigManager()
        assert mgr._coerce_value("3.14") == 3.14
        assert isinstance(mgr._coerce_value("3.14"), float)

    def test_coerce_value_returns_string(self):
        mgr = ConfigManager()
        assert mgr._coerce_value("hello") == "hello"
        assert isinstance(mgr._coerce_value("hello"), str)


class TestConfigManagerEnvLoading:
    def test_load_env_extracts_aios_vars(self, monkeypatch):
        monkeypatch.setenv("AIOS_DB_PATH", "/env/db.sqlite")
        monkeypatch.setenv("AIOS_LOG_LEVEL", "DEBUG")
        mgr = ConfigManager()
        env_config = mgr._load_env()
        assert env_config["db_path"] == "/env/db.sqlite"
        assert env_config["log_level"] == "DEBUG"

    def test_load_env_coerces_numeric_values(self, monkeypatch):
        monkeypatch.setenv("AIOS_AUDIT_RETENTION_DAYS", "180")
        monkeypatch.setenv("AIOS_APPROVAL_TIMEOUT", "7200")
        mgr = ConfigManager()
        env_config = mgr._load_env()
        assert env_config["audit_retention_days"] == 180
        assert env_config["approval_timeout"] == 7200

    def test_load_env_ignores_non_aios_vars(self, monkeypatch):
        monkeypatch.setenv("OTHER_VAR", "value")
        mgr = ConfigManager()
        env_config = mgr._load_env()
        assert "other_var" not in env_config


class TestConfigManagerWatchers:
    def test_watcher_called_on_override(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        calls = []
        mgr.add_watcher(lambda cfg: calls.append(cfg))
        mgr.add_override({"database": {"path": "/new/db.sqlite"}})
        assert len(calls) == 1
        assert calls[0]["database"]["path"] == "/new/db.sqlite"

    def test_watcher_exception_does_not_propagate(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()

        calls = []

        def bad_watcher(cfg):
            raise RuntimeError("watcher error")

        mgr.add_watcher(bad_watcher)
        mgr.add_watcher(lambda cfg: calls.append(cfg))
        mgr.add_override({"database": {"path": "/new/db.sqlite"}})
        assert len(calls) == 1
        assert calls[0]["database"]["path"] == "/new/db.sqlite"

    def test_stats_returns_correct_layer_count(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        stats = mgr.stats()
        assert stats["layers"] == 3
        assert stats["keys"] > 0
        assert stats["source"] == str(config_file)


class TestConfigManagerSave:
    def test_save_yaml_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        mgr = ConfigManager(str(config_file))
        mgr.add_override({"database": {"path": "/saved/db.sqlite"}})
        mgr.save()
        with open(config_file) as f:
            loaded = yaml.safe_load(f)
        assert loaded["database"]["path"] == "/saved/db.sqlite"

    def test_save_json_file(self, tmp_path):
        config_file = tmp_path / "config.json"
        mgr = ConfigManager(str(config_file))
        mgr.add_override({"database": {"path": "/saved/db.sqlite"}})
        mgr.save()
        with open(config_file) as f:
            loaded = json.load(f)
        assert loaded["database"]["path"] == "/saved/db.sqlite"


class TestConfigManagerEdgeCases:
    def test_load_malformed_yaml_raises(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("database:\n  path: /tmp/db\n  invalid: [unclosed")
        mgr = ConfigManager(str(config_file))
        with pytest.raises(yaml.YAMLError):
            mgr.load()

    def test_load_unreadable_file_graceful(self, tmp_path):
        config_file = tmp_path / "bad.json"
        config_file.write_text("{invalid json")
        mgr = ConfigManager(str(config_file))
        mgr.load()
        assert mgr.config == {}

    def test_load_json_file(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"database": {"path": "/json/db.sqlite"}}))
        mgr = ConfigManager(str(config_file))
        mgr.load()
        assert mgr.get_nested("database.path") == "/json/db.sqlite"

    def test_deep_merge_nested_dicts(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "database:\n  path: /tmp/db.sqlite\n  pool_size: 5\n"
        )
        mgr = ConfigManager(str(config_file))
        mgr.load()
        mgr.add_override({"database": {"timeout": 30}})
        assert mgr.get_nested("database.path") == "/tmp/db.sqlite"
        assert mgr.get_nested("database.pool_size") == 5
        assert mgr.get_nested("database.timeout") == 30

    def test_config_layer_dataclass(self):
        layer = ConfigLayer(name="test", source="file", config={"key": "val"}, priority=10)
        assert layer.name == "test"
        assert layer.source == "file"
        assert layer.config == {"key": "val"}
        assert layer.priority == 10

    def test_set_default_then_load(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database:\n  path: /tmp/db.sqlite\n")
        mgr = ConfigManager(str(config_file))
        mgr.set_default("logging", {"level": "WARNING"})
        mgr.load()
        assert mgr.get_nested("logging.level") == "WARNING"

    def test_set_multiple_defaults(self, tmp_path):
        mgr = ConfigManager(str(tmp_path / "config.yaml"))
        mgr.set_defaults({"database": {"path": "/default/db.sqlite"}, "audit": {"file_path": "/default/audit.jsonl"}})
        mgr.load()
        assert mgr.get_nested("database.path") == "/default/db.sqlite"
        assert mgr.get_nested("audit.file_path") == "/default/audit.jsonl"
