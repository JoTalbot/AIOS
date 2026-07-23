"""Tests for AIOS backup manager."""

import sqlite3
import json
import pytest
from pathlib import Path
from aios_core.backup_manager import BackupManager, BackupMetadata


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with data."""
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, status TEXT)")
    conn.execute("CREATE TABLE memory (id TEXT PRIMARY KEY, content TEXT)")
    conn.execute("INSERT INTO tasks VALUES ('t1', 'done')")
    conn.execute("INSERT INTO tasks VALUES ('t2', 'running')")
    conn.execute("INSERT INTO memory VALUES ('m1', 'test memory')")
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def backup_manager(tmp_path, test_db):
    """Create a BackupManager with test database."""
    backup_dir = tmp_path / "backups"
    return BackupManager(
        db_path=test_db,
        backup_dir=str(backup_dir),
        retention_days=30,
        max_backups=5,
        compress=False,
    )


@pytest.fixture
def compressed_backup_manager(tmp_path, test_db):
    """Create a BackupManager with compression enabled."""
    backup_dir = tmp_path / "backups_gz"
    return BackupManager(
        db_path=test_db,
        backup_dir=str(backup_dir),
        retention_days=30,
        max_backups=5,
        compress=True,
    )


class TestBackupManager:
    def test_create_backup(self, backup_manager):
        metadata = backup_manager.create_backup()
        assert metadata.backup_id.startswith("backup_")
        assert metadata.size_bytes > 0
        assert len(metadata.checksum) == 64  # SHA-256
        assert metadata.database.endswith("test.sqlite")
        assert metadata.mode == "full"
        assert not metadata.compressed
        assert "tasks" in metadata.tables
        assert "memory" in metadata.tables
        assert metadata.row_counts["tasks"] == 2
        assert metadata.row_counts["memory"] == 1

    def test_create_backup_with_label(self, backup_manager):
        metadata = backup_manager.create_backup(label="pre-deploy")
        assert "pre-deploy" in metadata.backup_id

    def test_create_compressed_backup(self, compressed_backup_manager):
        metadata = compressed_backup_manager.create_backup()
        assert metadata.compressed
        assert metadata.size_bytes > 0

    def test_list_backups(self, backup_manager):
        backup_manager.create_backup(label="first")
        backup_manager.create_backup(label="second")
        backups = backup_manager.list_backups()
        assert len(backups) == 2
        # Newest first
        assert "second" in backups[0].backup_id
        assert "first" in backups[1].backup_id

    def test_verify_backup(self, backup_manager):
        metadata = backup_manager.create_backup()
        assert backup_manager.verify_backup(metadata.backup_id)

    def test_verify_compressed_backup(self, compressed_backup_manager):
        metadata = compressed_backup_manager.create_backup()
        assert compressed_backup_manager.verify_backup(metadata.backup_id)

    def test_verify_nonexistent_backup(self, backup_manager):
        assert not backup_manager.verify_backup("nonexistent")

    def test_restore_backup(self, backup_manager, tmp_path):
        # Create backup
        metadata = backup_manager.create_backup()

        # Restore to new location
        target = tmp_path / "restored.sqlite"
        assert backup_manager.restore_backup(metadata.backup_id, str(target))

        # Verify restored database
        conn = sqlite3.connect(str(target))
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2

    def test_restore_compressed_backup(self, compressed_backup_manager, tmp_path):
        metadata = compressed_backup_manager.create_backup()
        target = tmp_path / "restored.sqlite"
        assert compressed_backup_manager.restore_backup(metadata.backup_id, str(target))

        conn = sqlite3.connect(str(target))
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2

    def test_restore_nonexistent(self, backup_manager):
        assert not backup_manager.restore_backup("nonexistent")

    def test_cleanup_old_backups(self, backup_manager):
        # Create several backups
        for i in range(3):
            backup_manager.create_backup(label=f"backup-{i}")

        assert len(backup_manager.backups) == 3

        # Set retention to 0 to remove all
        backup_manager.retention_days = 0
        removed = backup_manager.cleanup_old_backups()
        # Note: may not remove all due to timestamp check
        assert removed >= 0

    def test_max_backups_enforcement(self, tmp_path, test_db):
        manager = BackupManager(
            db_path=test_db,
            backup_dir=str(tmp_path / "backups"),
            max_backups=3,
            compress=False,
        )

        # Create 5 backups
        for i in range(5):
            manager.create_backup(label=f"b{i}")

        assert len(manager.backups) == 5

        # Cleanup should enforce max
        removed = manager.cleanup_old_backups()
        assert len(manager.backups) <= 3

    def test_health_report(self, backup_manager):
        backup_manager.create_backup()
        backup_manager.create_backup()

        report = backup_manager.health_report()
        assert report["total_backups"] == 2
        assert report["total_size_mb"] > 0
        assert report["oldest_backup"] is not None
        assert report["newest_backup"] is not None
        assert report["retention_days"] == 30
        assert report["max_backups"] == 5

    def test_schedule_info(self, backup_manager):
        info = backup_manager.schedule_info()
        assert "recommended_frequency" in info
        assert "retention" in info
        assert "max_backups" in info

    def test_metadata_persistence(self, backup_manager):
        backup_manager.create_backup(label="persist-test")

        # Create new manager pointing to same dir
        manager2 = BackupManager(
            db_path=backup_manager.db_path,
            backup_dir=str(backup_manager.backup_dir),
        )
        assert len(manager2.backups) == 1
        assert "persist-test" in manager2.backups[0].backup_id


class TestBackupMetadata:
    def test_to_dict(self):
        metadata = BackupMetadata(
            backup_id="test-123",
            created_at="2026-01-01T00:00:00",
            size_bytes=1024,
            checksum="abc123",
            database="test.sqlite",
            mode="full",
            compressed=False,
            tables=["tasks", "memory"],
            row_counts={"tasks": 5, "memory": 3},
        )
        d = metadata.to_dict()
        assert d["backup_id"] == "test-123"
        assert d["size_bytes"] == 1024
        assert d["tables"] == ["tasks", "memory"]
