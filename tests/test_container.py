"""Tests for DI container."""
from aios_core.container import AppConfig, AppContainer


def test_config_defaults():
    cfg = AppConfig()
    assert cfg.db_path == "aios.sqlite"
    assert cfg.backup_dir == "./backups"
    assert cfg.constitution_dir == "docs/constitution"
    assert cfg.backup_retention_days == 30
    assert cfg.backup_max_count == 10
    assert cfg.backup_compress is False


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("AIOS_DB_PATH", "/custom/path.db")
    monkeypatch.setenv("AIOS_BACKUP_DIR", "/custom/backups")
    monkeypatch.setenv("AIOS_BACKUP_COMPRESS", "true")
    cfg = AppConfig.from_env()
    assert cfg.db_path == "/custom/path.db"
    assert cfg.backup_dir == "/custom/backups"
    assert cfg.backup_compress is True


def test_container_singleton():
    c = AppContainer(AppConfig(db_path=":memory:"))
    db1 = c.db()
    db2 = c.db()
    assert db1 is db2  # same instance
    orch1 = c.orchestrator()
    orch2 = c.orchestrator()
    assert orch1 is orch2


def test_container_configure():
    c = AppContainer(AppConfig(db_path=":memory:"))
    assert c.config.backup_dir == "./backups"
    c.configure(backup_dir="/custom/bu")
    assert c.config.backup_dir == "/custom/bu"


def test_container_reset():
    c = AppContainer(AppConfig(db_path=":memory:"))
    db1 = c.db()
    c.orchestrator()
    c.reset()
    assert c.stats()["db_ready"] is False
    db2 = c.db()
    assert db1 is not db2  # new instance after reset


def test_container_stats():
    c = AppContainer(AppConfig(db_path=":memory:"))
    s = c.stats()
    assert s["db_path"] == ":memory:"
    assert s["db_ready"] is False
    assert s["orch_ready"] is False
    c.db()
    assert c.stats()["db_ready"] is True


def test_container_data_exporters():
    c = AppContainer(AppConfig(db_path=":memory:"))
    de = c.data_exporter()
    di = c.data_importer()
    assert de is not None
    assert di is not None


def test_container_backup_manager():
    c = AppContainer(AppConfig(db_path=":memory:", backup_dir="/tmp/bu"))
    bm = c.backup_manager()
    r = bm.health_report()
    assert "total_backups" in r
