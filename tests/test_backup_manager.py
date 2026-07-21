"""Tests for Hot Backup and Disaster Recovery Engine (Milestone 4.2.2)."""

import os
import sqlite3
import pytest
from aios_core.backup_manager import BackupManager


def test_backup_and_recovery(tmp_path):
    db_file = tmp_path / "test_aios.sqlite"
    backup_dir = tmp_path / "backups"

    # Seed primary database
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO records (name) VALUES ('initial_state');")
    conn.commit()
    conn.close()

    bm = BackupManager(db_path=str(db_file), backup_dir=str(backup_dir), max_backups=2)

    # Create backup snapshot
    meta = bm.create_backup(label="pre_update")
    assert os.path.exists(meta["path"])
    assert meta["sha256"] != ""

    # Modify primary database
    conn = sqlite3.connect(str(db_file))
    conn.execute("INSERT INTO records (name) VALUES ('corrupted_or_modified_state');")
    conn.commit()
    conn.close()

    # Verify modification
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM records;")
    count_before = cur.fetchone()[0]
    conn.close()
    assert count_before == 2

    # Restore from backup
    restored = bm.restore_backup(meta["backup_id"])
    assert restored is True

    # Verify original state restored
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM records;")
    count_after = cur.fetchone()[0]
    conn.close()
    assert count_after == 1


def test_backup_retention_policy(tmp_path):
    db_file = tmp_path / "test_aios_retention.sqlite"
    backup_dir = tmp_path / "backups_retention"

    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE meta (k TEXT);")
    conn.commit()
    conn.close()

    bm = BackupManager(db_path=str(db_file), backup_dir=str(backup_dir), max_backups=3)

    # Create 5 backups
    for i in range(5):
        bm.create_backup(label=f"snap_{i}")

    # Should only retain max_backups=3 snapshots
    active_backups = bm.list_backups()
    assert len(active_backups) == 3
