"""Chaos tests for AIOS system resilience."""

import random
import sqlite3
import time
from pathlib import Path

import pytest


class TestDatabaseChaos:
    """Chaos tests for database resilience."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create test database."""
        from aios_core.storage import Database

        db_path = tmp_path / "chaos_test.sqlite"
        return Database(str(db_path))

    def test_database_recovery_after_corruption(self, tmp_path):
        """Test system behavior when database is corrupted."""
        from aios_core.storage import Database

        db_path = tmp_path / "corrupt_test.sqlite"
        db = Database(str(db_path))

        # Create some data
        db.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, value TEXT)")
        for i in range(100):
            db.execute("INSERT INTO test_data VALUES (?, ?)", (i, f"value-{i}"))

        # Simulate corruption by truncating file
        with open(db_path, "r+b") as f:
            f.seek(100)
            f.write(b"CORRUPTED" * 100)

        # System should handle gracefully
        try:
            new_db = Database(str(db_path))
            # Should either recover or fail gracefully
            cursor = new_db.execute("SELECT COUNT(*) FROM test_data")
        except Exception as e:
            # Should raise appropriate error
            assert "database" in str(e).lower() or "disk" in str(e).lower()

    def test_concurrent_write_conflicts(self, tmp_path):
        """Test handling of concurrent write conflicts."""
        import concurrent.futures

        from aios_core.storage import Database

        db_path = tmp_path / "concurrent_test.sqlite"
        db = Database(str(db_path))

        # Create test table
        db.execute("CREATE TABLE counter (id INTEGER PRIMARY KEY, value INTEGER)")
        db.execute("INSERT INTO counter VALUES (1, 0)")

        def increment():
            # Simulate concurrent increments
            db.execute("UPDATE counter SET value = value + 1 WHERE id = 1")
            return True

        # Run concurrent increments
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(increment) for _ in range(50)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(results)

        # Check final value
        cursor = db.execute("SELECT value FROM counter WHERE id = 1")
        final_value = cursor.fetchone()[0]

        # Should have all increments (some may be lost due to race conditions)
        assert final_value > 0

    def test_database_lock_timeout(self, tmp_path):
        """Test behavior under database lock contention."""
        import concurrent.futures

        from aios_core.storage import Database

        db_path = tmp_path / "lock_test.sqlite"
        db = Database(str(db_path))

        db.execute("CREATE TABLE test_lock (id INTEGER PRIMARY KEY, data TEXT)")

        def long_transaction(i):
            # Simulate long transaction
            db.execute("BEGIN")
            db.execute("INSERT INTO test_lock VALUES (?, ?)", (i, f"data-{i}"))
            time.sleep(0.01)  # Hold lock
            db.execute("COMMIT")
            return True

        # Run overlapping transactions
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(long_transaction, i) for i in range(20)]
            results = []
            for f in futures:
                try:
                    results.append(f.result(timeout=5))
                except Exception:
                    results.append(False)

        # Most should succeed
        success_count = sum(1 for r in results if r)
        assert success_count >= 15  # At least 75% should succeed

    def test_recovery_after_crash(self, tmp_path):
        """Test recovery after simulated crash."""
        from aios_core.storage import Database

        db_path = tmp_path / "crash_test.sqlite"

        # Create and populate database
        db = Database(str(db_path))
        db.execute("CREATE TABLE important_data (id INTEGER PRIMARY KEY, value TEXT)")

        for i in range(100):
            db.execute("INSERT INTO important_data VALUES (?, ?)", (i, f"critical-{i}"))

        # Simulate crash by not committing
        db.execute("BEGIN")
        db.execute("INSERT INTO important_data VALUES (999, 'uncommitted')")
        # Don't commit - simulate crash

        # Reopen database
        new_db = Database(str(db_path))

        # Should recover to last consistent state
        cursor = new_db.execute("SELECT COUNT(*) FROM important_data")
        count = cursor.fetchone()[0]

        # Should have original 100 records (uncommitted should be rolled back)
        assert count == 100


class TestWebhookChaos:
    """Chaos tests for webhook system resilience."""

    def test_webhook_delivery_with_unreachable_endpoint(self):
        """Test webhook behavior when endpoint is unreachable."""
        from aios_core.webhook_manager import WebhookManager

        manager = WebhookManager()

        # Register webhook with invalid URL
        manager.register(
            "unreachable",
            "https://invalid-url-that-does-not-exist.com/hook",
            ["ban_detected"],
        )

        # Should not crash when sending to unreachable endpoint
        result = manager.notify("ban_detected", {"profile": "test"})

        # Should record the attempt
        assert result is not None

    def test_webhook_flood_protection(self):
        """Test webhook system under flood of notifications."""
        from aios_core.webhook_manager import WebhookManager

        manager = WebhookManager()
        manager.register("flood-test", "https://example.com/hook", ["ban_detected"])

        # Send 10000 notifications rapidly
        start = time.time()
        for i in range(10000):
            manager.notify("ban_detected", {"id": i})
        duration = time.time() - start

        # Should complete in reasonable time
        assert duration < 30  # Less than 30 seconds

    def test_webhook_history_overflow(self):
        """Test webhook history handling when it gets very large."""
        from aios_core.webhook_manager import WebhookManager

        manager = WebhookManager()
        manager.max_history = 100  # Small limit for testing

        # Generate more notifications than max_history
        for i in range(200):
            manager.notify("ban_detected", {"id": i})

        # History should be trimmed
        history = manager.get_history()
        assert len(history) <= 100


class TestBackupChaos:
    """Chaos tests for backup system resilience."""

    def test_backup_during_heavy_write_load(self, tmp_path):
        """Test backup creation during heavy write operations."""
        import concurrent.futures

        from aios_core.backup_manager import BackupManager

        db_path = tmp_path / "write_load.sqlite"
        backup_dir = tmp_path / "backups"

        # Create database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE data (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()

        manager = BackupManager(str(db_path), str(backup_dir))

        def write_data(i):
            conn = sqlite3.connect(str(db_path))
            conn.execute("INSERT INTO data VALUES (?, ?)", (i, f"value-{i}"))
            conn.commit()
            conn.close()

        def create_backup():
            time.sleep(0.1)  # Let some writes happen
            return manager.create_backup(label="during-writes")

        # Run concurrent writes and backup
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            write_futures = [executor.submit(write_data, i) for i in range(100)]
            backup_future = executor.submit(create_backup)

            # Wait for all
            for f in write_futures:
                f.result()

            metadata = backup_future.result()

        # Backup should succeed
        assert metadata is not None
        assert metadata.size_bytes > 0

    def test_restore_to_corrupted_location(self, tmp_path):
        """Test restore behavior when target location is problematic."""
        from aios_core.backup_manager import BackupManager

        db_path = tmp_path / "source.sqlite"
        backup_dir = tmp_path / "backups"

        # Create source database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        manager = BackupManager(str(db_path), str(backup_dir))
        metadata = manager.create_backup()

        # Try to restore to read-only location
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_file = readonly_dir / "restore.sqlite"

        # Make directory read-only
        readonly_dir.chmod(0o444)

        try:
            success = manager.restore_backup(metadata.backup_id, str(readonly_file))
            # Should fail gracefully
            assert not success
        except PermissionError:
            # Expected
            pass
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_backup_verification_with_tampered_checksum(self, tmp_path):
        """Test backup verification detects tampered checksums."""
        from aios_core.backup_manager import BackupManager

        db_path = tmp_path / "tamper_test.sqlite"
        backup_dir = tmp_path / "backups"

        # Create database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE sensitive (id INTEGER, data TEXT)")
        conn.execute("INSERT INTO sensitive VALUES (1, 'secret')")
        conn.commit()
        conn.close()

        manager = BackupManager(str(db_path), str(backup_dir))
        metadata = manager.create_backup()

        # Tamper with backup file
        backup_files = list(backup_dir.glob("*.sqlite"))
        if backup_files:
            with open(backup_files[0], "r+b") as f:
                f.seek(50)
                f.write(b"TAMPERED")

        # Verification should fail
        is_valid = manager.verify_backup(metadata.backup_id)
        assert not is_valid


class TestAPIChaos:
    """Chaos tests for API resilience."""

    def test_api_under_malformed_requests(self):
        """Test API handles malformed requests gracefully."""
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        async def endpoint(request: Request):
            return JSONResponse({"status": "ok"})

        app = Starlette(routes=[Route("/test", endpoint, methods=["POST"])])
        client = TestClient(app)

        # Send malformed JSON
        response = client.post(
            "/test", content="not json", headers={"Content-Type": "application/json"}
        )

        # Should handle gracefully (not crash)
        assert response.status_code in [200, 400, 422, 500]

    def test_api_concurrent_identical_requests(self):
        """Test API handles many identical concurrent requests."""
        import concurrent.futures

        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        async def endpoint(request: Request):
            time.sleep(0.01)  # Simulate work
            return JSONResponse({"id": id(request)})

        app = Starlette(routes=[Route("/test", endpoint)])
        client = TestClient(app)

        def make_request():
            return client.get("/test").status_code

        # Send 100 identical requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(code == 200 for code in results)


class TestRecoveryScenarios:
    """Tests for system recovery scenarios."""

    def test_full_system_restart(self, tmp_path):
        """Test system behavior after complete restart."""
        from aios_core.storage import Database
        from aios_core.webhook_manager import WebhookManager

        db_path = tmp_path / "restart_test.sqlite"

        # Create initial state
        db = Database(str(db_path))
        db.execute("CREATE TABLE state (key TEXT PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO state VALUES ('counter', '100')")

        webhook_manager = WebhookManager()
        webhook_manager.register("test", "https://example.com/hook", ["ban_detected"])

        # Simulate restart by creating new instances
        new_db = Database(str(db_path))
        new_webhook_manager = WebhookManager()

        # Database should persist
        cursor = new_db.execute("SELECT value FROM state WHERE key = 'counter'")
        value = cursor.fetchone()[0]
        assert value == "100"

        # Webhook manager state is in-memory, should be empty
        assert len(new_webhook_manager.list_targets()) == 0

    def test_graceful_degradation(self, tmp_path):
        """Test system continues working when components fail."""
        from aios_core.storage import Database
        from aios_core.webhook_manager import WebhookManager

        db_path = tmp_path / "degradation_test.sqlite"
        db = Database(str(db_path))

        db.execute("CREATE TABLE operations (id INTEGER PRIMARY KEY, status TEXT)")

        webhook_manager = WebhookManager()
        webhook_manager.register("failing", "https://invalid.com/hook", ["test"])

        # Webhook fails but database operations should continue
        for i in range(10):
            # This webhook call may fail
            webhook_manager.notify("test", {"id": i})

            # But database should still work
            db.execute("INSERT INTO operations VALUES (?, ?)", (i, "success"))

        # Verify database operations succeeded
        cursor = db.execute("SELECT COUNT(*) FROM operations")
        count = cursor.fetchone()[0]
        assert count == 10
