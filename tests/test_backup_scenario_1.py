"""Backup scenario test."""
from aios_core.backup_manager import BackupManager

def test_backup():
    bm = BackupManager(':memory:', backup_dir='/tmp/tb')
    assert bm is not None

def test_health():
    bm = BackupManager(':memory:', backup_dir='/tmp/tb')
    assert 'total_backups' in bm.health_report()
