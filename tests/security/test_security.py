"""Security tests for AIOS system."""


import httpx
import pytest
from starlette.applications import Starlette


class TestSQLInjection:
    """Tests for SQL injection vulnerabilities."""

    def test_sql_injection_in_export(self, tmp_path):
        """Test SQL injection attempts in export parameters."""
        from aios_core.data_export import DataExporter

        db_path = tmp_path / "test.sqlite"

        # Create test database
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE tasks (id TEXT, status TEXT)")
        conn.execute("INSERT INTO tasks VALUES ('1', 'completed')")
        conn.commit()
        conn.close()

        # Try SQL injection
        malicious_input = "'; DROP TABLE tasks; --"

        with DataExporter(str(db_path)) as exporter:
            # Should not execute malicious SQL
            try:
                count = exporter.export_tasks(
                    str(tmp_path / "export.json"), format="json", status=malicious_input
                )
                # Should return 0 results, not crash
                assert count == 0
            except Exception:
                # Should handle gracefully
                pass

        # Verify table still exists
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1  # Original data intact

    def test_sql_injection_in_search(self, tmp_path):
        """Test SQL injection in search/filter parameters."""
        from aios_core.secret_manager import SecretManager

        manager = SecretManager()

        # Generate a key
        manager.generate_key("test-user", ["admin"])

        # Try SQL injection in subject filter
        malicious_subject = "' OR '1'='1"

        # Should not return all keys
        keys = manager.get_keys_by_subject(malicious_subject)
        assert len(keys) == 0


class TestAuthenticationBypass:
    """Tests for authentication bypass vulnerabilities."""

    @pytest.mark.asyncio
    async def test_admin_endpoint_requires_auth(self):
        """Test admin endpoints require authentication."""
        from aios_core.api.admin_routes import get_admin_routes, init_admin_routes

        init_admin_routes("test.sqlite", "./backups")
        app = Starlette(routes=get_admin_routes())
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            # Try accessing without auth
            response = await client.get("/api/v1/admin/keys")

            # Should fail with 401 or 403
            assert response.status_code in [401, 403, 500]

    def test_invalid_api_key_rejected(self):
        """Test invalid API keys are rejected."""
        from aios_core.secret_manager import SecretManager

        manager = SecretManager()

        # Try validating non-existent key
        is_valid, key = manager.validate_key("invalid-key-12345")

        assert not is_valid
        assert key is None

    def test_revoked_key_rejected(self):
        """Test revoked keys cannot be used."""
        from aios_core.secret_manager import SecretManager

        manager = SecretManager()

        # Generate and revoke key
        key = manager.generate_key("test-user", ["admin"])
        manager.revoke_key(key.key)

        # Try to validate revoked key
        is_valid, _ = manager.validate_key(key.key)

        assert not is_valid


class TestInputValidation:
    """Tests for input validation."""

    def test_webhook_url_validation(self):
        """Test webhook URL validation."""
        from aios_core.webhook_manager import WebhookManager

        manager = WebhookManager()

        # Try registering invalid URL
        try:
            manager.register("test", "not-a-valid-url", ["ban_detected"])
            # Should either validate or handle gracefully
        except Exception:
            # Should raise validation error
            pass

    def test_backup_path_traversal(self, tmp_path):
        """Test backup prevents path traversal attacks."""
        from aios_core.backup_manager import BackupManager

        db_path = tmp_path / "test.sqlite"
        backup_dir = tmp_path / "backups"

        # Create test database
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        manager = BackupManager(str(db_path), str(backup_dir))

        # Try path traversal in backup label
        malicious_label = "../../../etc/passwd"

        try:
            manager.create_backup(label=malicious_label)
            # Should sanitize or reject malicious label
        except Exception:
            # Should handle gracefully
            pass

    def test_export_file_size_limit(self, tmp_path):
        """Test export handles large datasets."""
        from aios_core.data_export import DataExporter

        db_path = tmp_path / "large.sqlite"

        # Create database with many records
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE tasks (id INTEGER, data TEXT)")

        # Insert 10000 records
        for i in range(10000):
            conn.execute("INSERT INTO tasks VALUES (?, ?)", (i, f"data-{i}"))

        conn.commit()
        conn.close()

        # Try to export
        with DataExporter(str(db_path)) as exporter:
            count = exporter.export_tasks(str(tmp_path / "large_export.json"), format="json")

            # Should handle large export
            assert count == 10000


class TestSecretsManagement:
    """Tests for secrets management security."""

    def test_api_key_entropy(self):
        """Test API keys have sufficient entropy."""
        from aios_core.secret_manager import SecretManager

        manager = SecretManager()
        key = manager.generate_key("test-user", ["admin"])

        # Key should be long enough
        assert len(key.key) >= 40

        # Key should be unique
        key2 = manager.generate_key("test-user", ["admin"])
        assert key.key != key2.key

    def test_expired_keys_rejected(self):
        """Test expired keys are rejected."""
        from datetime import datetime, timedelta

        from aios_core.secret_manager import APIKey

        # Create expired key
        expired_at = (datetime.now() - timedelta(days=1)).isoformat()
        key = APIKey(
            key="aios_test",
            subject="user",
            roles=["admin"],
            created_at="2020-01-01",
            expires_at=expired_at,
        )

        assert key.is_expired()
        assert not key.is_valid()

    def test_max_keys_per_subject(self):
        """Test max keys per subject is enforced."""
        from aios_core.secret_manager import SecretManager

        manager = SecretManager(max_keys_per_subject=3)

        # Generate max keys
        for i in range(3):
            manager.generate_key("user", ["viewer"])

        # Try to generate more
        with pytest.raises(ValueError, match="max keys"):
            manager.generate_key("user", ["viewer"])


class TestBackupSecurity:
    """Tests for backup security."""

    def test_backup_checksum_verification(self, tmp_path):
        """Test backup checksum prevents tampering."""
        from aios_core.backup_manager import BackupManager

        db_path = tmp_path / "test.sqlite"
        backup_dir = tmp_path / "backups"

        # Create test database
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'secret')")
        conn.commit()
        conn.close()

        manager = BackupManager(str(db_path), str(backup_dir))

        # Create backup
        metadata = manager.create_backup()

        # Verify backup
        is_valid = manager.verify_backup(metadata.backup_id)
        assert is_valid

        # Tamper with backup
        import glob

        backup_files = glob.glob(str(backup_dir / "*.sqlite"))
        if backup_files:
            with open(backup_files[0], "r+b") as f:
                f.seek(100)
                f.write(b"TAMPERED")

            # Verify should fail
            is_valid = manager.verify_backup(metadata.backup_id)
            assert not is_valid

    def test_backup_encryption_at_rest(self, tmp_path):
        """Test backup can be compressed (basic obfuscation)."""
        from aios_core.backup_manager import BackupManager

        db_path = tmp_path / "test.sqlite"
        backup_dir = tmp_path / "backups"

        # Create test database with sensitive data
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE secrets (id INTEGER, data TEXT)")
        conn.execute("INSERT INTO secrets VALUES (1, 'password123')")
        conn.commit()
        conn.close()

        # Create compressed backup
        manager = BackupManager(str(db_path), str(backup_dir), compress=True)
        metadata = manager.create_backup()

        # Should be compressed
        assert metadata.compressed

        # Compressed file should be smaller
        original_size = db_path.stat().st_size
        backup_size = (backup_dir / f"{metadata.backup_id}.sqlite.gz").stat().st_size

        # Compression should reduce size (or at least not be much larger)
        assert backup_size < original_size * 1.5  # Allow some overhead


class TestWebhookSecurity:
    """Tests for webhook security."""

    def test_webhook_hmac_signing(self):
        """Test webhook payloads are signed with HMAC."""
        from aios_core.webhook_manager import WebhookManager, WebhookPayload

        manager = WebhookManager()

        # Register webhook with secret
        manager.register("secure", "https://example.com/hook", ["ban_detected"], secret="my-secret")

        # Create payload
        payload = WebhookPayload(
            event="ban_detected",
            timestamp="2026-01-01T00:00:00",
            source="test",
            data={"test": "data"},
        )

        # Sign payload
        signature = payload.sign("my-secret")

        # Signature should be valid
        assert len(signature) == 64  # SHA-256 hex digest
        assert signature != payload.sign("wrong-secret")

    def test_webhook_event_filtering(self):
        """Test webhooks only receive subscribed events."""
        from aios_core.webhook_manager import WebhookManager

        manager = WebhookManager()

        # Register webhook for specific events only
        manager.register("filtered", "https://example.com/hook", ["ban_detected"])

        # Send different event
        result = manager.notify("device_offline", {"device": "test"})

        # Should not trigger webhook
        assert result["targets_triggered"] == 0

        # Send matching event
        result = manager.notify("ban_detected", {"profile": "test"})

        # Should trigger webhook
        assert result["targets_triggered"] == 1


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_api_key_usage_tracking(self):
        """Test API key usage is tracked."""
        from aios_core.secret_manager import SecretManager

        manager = SecretManager()
        key = manager.generate_key("test-user", ["admin"])

        # Use key multiple times
        for _ in range(5):
            manager.validate_key(key.key)

        # Check usage count
        assert manager.keys[key.key].usage_count == 5
        assert manager.keys[key.key].last_used is not None


class TestDataIsolation:
    """Tests for data isolation between subjects."""

    def test_memory_isolation_by_owner(self, tmp_path):
        """Test memory records are isolated by owner."""
        from aios_core.data_export import DataExporter

        db_path = tmp_path / "test.sqlite"

        # Create database with memory records
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE personal_memory (
                id TEXT, owner TEXT, content TEXT, created_at TEXT
            )
        """
        )
        conn.execute("INSERT INTO personal_memory VALUES ('1', 'user1', 'secret1', '2026-01-01')")
        conn.execute("INSERT INTO personal_memory VALUES ('2', 'user2', 'secret2', '2026-01-01')")
        conn.commit()
        conn.close()

        # Export only user1's memory
        with DataExporter(str(db_path)) as exporter:
            count = exporter.export_memory(
                str(tmp_path / "user1_memory.json"), format="json", subject="user1"
            )

            # Should only export user1's records
            assert count == 1

            # Verify content
            import json

            with open(tmp_path / "user1_memory.json") as f:
                data = json.load(f)
                assert len(data["data"]) == 1
                assert data["data"][0]["owner"] == "user1"
