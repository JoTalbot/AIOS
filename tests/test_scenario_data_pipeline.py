"""Data pipeline scenario — export, backup, store."""
from aios_core.storage import Database
from aios_core.data_export import DataExporter
from aios_core.backup_manager import BackupManager

def test_data_flow():
    db = Database(":memory:")
    assert db.stats()["dialect"] == "sqlite"
    de = DataExporter(":memory:")
    assert de is not None
    bm = BackupManager(":memory:", backup_dir="/tmp/test_bu")
    r = bm.health_report()
    assert "total_backups" in r
