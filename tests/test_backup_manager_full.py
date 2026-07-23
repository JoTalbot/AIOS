"""Backup manager full new."""
from aios_core.backup_manager import BackupManager
def test(): bm=BackupManager(":memory:",backup_dir="/tmp/b"); assert bm is not None
