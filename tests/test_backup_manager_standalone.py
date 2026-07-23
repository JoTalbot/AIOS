"""Backup manager standalone test."""
from aios_core.backup_manager import BackupManager
def test_init(): assert BackupManager(":memory:") is not None
