"""Integration tests for backup and restore operations."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from aios_core.backup_manager import BackupManager


class TestBackupRestoreIntegration:
    """End-to-end tests for backup and restore workflows."""

    @pytest.fixture
    def production_db(self, tmp_path):
        """Create a production-like database with realistic data."""
        db_path = tmp_path / "production.sqlite"
        conn = sqlite3.connect(str(db_path))

        # Create tables
        conn.execute(
            """
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                data TEXT
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE personal_memory (
                id TEXT PRIMARY KEY,
                owner TEXT,
                content TEXT,
                created_at TEXT
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE audit_log (
                id TEXT PRIMARY KEY,
                event_type TEXT,
                timestamp TEXT,
                details TEXT
            )
        """
        )

        # Insert realistic data
        for i in range(100):
            conn.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?)",
                (
                    f"task-{i}",
                    "completed" if i % 2 == 0 else "running",
                    f"2026-01-{i % 28 + 1:02d}",
                    f"2026-07-{i % 28 + 1:02d}",
                    f'{{"data": "value-{i}"}}',
                ),
            )

        for i in range(50):
            conn.execute(
                "INSERT INTO personal_memory VALUES (?, ?, ?, ?)",
                (f"mem-{i}", f"user-{i % 5}", f"Memory content {i}", f"2026-07-{i % 28 + 1:02d}"),
            )

        for i in range(200):
            conn.execute(
                "INSERT INTO audit_log VALUES (?, ?, ?, ?)",
                (
                    f"log-{i}",
                    "task.create" if i % 3 == 0 else "task.update",
                    f"2026-07-{i % 28 + 1:02d}T{i % 24:02d}:00:00",
                    f'{{"action": "action-{i}"}}',
                ),
            )

        conn.commit()
        conn.close()

        return str(db_path)

    def test_full_backup_restore_cycle(self, production_db, tmp_path):
        """Test complete backup and restore cycle."""
        backup_dir = tmp_path / "backups"

        # Create backup
        manager = BackupManager(db_path=production_db, backup_dir=str(backup_dir), compress=False)

        metadata = manager.create_backup(label="integration-test")

        # Verify backup was created
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob("*.sqlite"))
        assert len(backup_files) == 1

        # Restore to new location
        restored_db = tmp_path / "restored.sqlite"
        success = manager.restore_backup(metadata.backup_id, str(restored_db))
        assert success

        # Verify restored database
        conn = sqlite3.connect(str(restored_db))

        # Check tasks
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        task_count = cursor.fetchone()[0]
        assert task_count == 100, f"Expected 100 tasks, got {task_count}"

        # Check memory
        cursor = conn.execute("SELECT COUNT(*) FROM personal_memory")
        memory_count = cursor.fetchone()[0]
        assert memory_count == 50, f"Expected 50 memory records, got {memory_count}"

        # Check audit log
        cursor = conn.execute("SELECT COUNT(*) FROM audit_log")
        audit_count = cursor.fetchone()[0]
        assert audit_count == 200, f"Expected 200 audit logs, got {audit_count}"

        # Verify data integrity
        cursor = conn.execute("SELECT data FROM tasks WHERE id = 'task-0'")
        data = cursor.fetchone()[0]
        assert data == '{"data": "value-0"}'

        conn.close()

    def test_compressed_backup_restore(self, production_db, tmp_path):
        """Test backup and restore with compression."""
        backup_dir = tmp_path / "backups_gz"

        # Create compressed backup
        manager = BackupManager(db_path=production_db, backup_dir=str(backup_dir), compress=True)

        metadata = manager.create_backup(label="compressed-test")

        # Verify compressed backup
        assert metadata.compressed
        backup_files = list(backup_dir.glob("*.sqlite.gz"))
        assert len(backup_files) == 1

        # Verify compression saved space
        original_size = Path(production_db).stat().st_size
        backup_size = backup_files[0].stat().st_size
        assert backup_size < original_size, "Compressed backup should be smaller"

        # Restore
        restored_db = tmp_path / "restored.sqlite"
        success = manager.restore_backup(metadata.backup_id, str(restored_db))
        assert success

        # Verify data
        conn = sqlite3.connect(str(restored_db))
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        assert cursor.fetchone()[0] == 100
        conn.close()

    def test_backup_verification(self, production_db, tmp_path):
        """Test backup integrity verification."""
        backup_dir = tmp_path / "backups"

        manager = BackupManager(db_path=production_db, backup_dir=str(backup_dir))

        # Create backup
        metadata = manager.create_backup(label="verify-test")

        # Verify valid backup
        is_valid = manager.verify_backup(metadata.backup_id)
        assert is_valid, "Valid backup should pass verification"

        # Corrupt backup
        backup_files = list(backup_dir.glob("*.sqlite"))
        if backup_files:
            with open(backup_files[0], "r+b") as f:
                f.seek(100)
                f.write(b"CORRUPTED")

            # Verify corrupted backup fails
            is_valid = manager.verify_backup(metadata.backup_id)
            assert not is_valid, "Corrupted backup should fail verification"

    def test_multiple_backups_rotation(self, production_db, tmp_path):
        """Test backup rotation with multiple backups."""
        backup_dir = tmp_path / "backups"

        manager = BackupManager(
            db_path=production_db, backup_dir=str(backup_dir), max_backups=3, retention_days=30
        )

        # Create 5 backups
        backup_ids = []
        for i in range(5):
            metadata = manager.create_backup(label=f"rotation-{i}")
            backup_ids.append(metadata.backup_id)

        # Should have created 5 backups
        assert len(manager.backups) == 5

        # Cleanup should enforce max_backups
        removed = manager.cleanup_old_backups()

        # Should keep only max_backups
        assert len(manager.backups) <= 3

    def test_backup_restore_with_schema_changes(self, tmp_path):
        """Test backup and restore after schema changes."""
        db_path = tmp_path / "schema_test.sqlite"
        backup_dir = tmp_path / "backups"

        # Create initial database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO users VALUES (1, 'Alice')")
        conn.commit()
        conn.close()

        # Create backup
        manager = BackupManager(db_path=str(db_path), backup_dir=str(backup_dir))
        metadata = manager.create_backup(label="before-schema-change")

        # Modify schema
        conn = sqlite3.connect(str(db_path))
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.execute("UPDATE users SET email = 'alice@example.com' WHERE id = 1")
        conn.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT)")
        conn.execute("INSERT INTO posts VALUES (1, 1, 'Hello World')")
        conn.commit()
        conn.close()

        # Restore original backup
        restored_db = tmp_path / "restored.sqlite"
        success = manager.restore_backup(metadata.backup_id, str(restored_db))
        assert success

        # Verify restored to original schema
        conn = sqlite3.connect(str(restored_db))

        # Should have users table without email column
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "email" not in columns, "Restored DB should not have email column"

        # Should not have posts table
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "posts" not in tables, "Restored DB should not have posts table"

        conn.close()

    def test_backup_with_concurrent_access(self, production_db, tmp_path):
        """Test backup while database is being accessed."""
        backup_dir = tmp_path / "backups"

        # Start backup
        manager = BackupManager(db_path=production_db, backup_dir=str(backup_dir))

        # Simulate concurrent access
        conn = sqlite3.connect(production_db)
        conn.execute(
            "INSERT INTO tasks VALUES ('concurrent-task', 'running', '2026-07-23', '2026-07-23', '{}')"
        )

        # Create backup while connection is open
        metadata = manager.create_backup(label="concurrent-test")

        conn.commit()
        conn.close()

        # Verify backup was created successfully
        assert metadata is not None
        assert metadata.size_bytes > 0

        # Restore and verify
        restored_db = tmp_path / "restored.sqlite"
        success = manager.restore_backup(metadata.backup_id, str(restored_db))
        assert success

        conn = sqlite3.connect(str(restored_db))
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        conn.close()

        # Should have at least the original 100 tasks
        assert count >= 100
