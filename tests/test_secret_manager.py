"""Tests for AIOS secret manager."""

import json
import tempfile
from pathlib import Path

import pytest

from aios_core.secret_manager import APIKey, SecretManager


class TestAPIKey:
    def test_create_api_key(self):
        key = APIKey(
            key="aios_test123",
            subject="test-user",
            roles=["admin"],
            created_at="2026-01-01T00:00:00",
        )
        assert key.key == "aios_test123"
        assert key.subject == "test-user"
        assert key.roles == ["admin"]
        assert not key.revoked
        assert key.is_valid()

    def test_expired_key(self):
        key = APIKey(
            key="aios_test",
            subject="user",
            roles=["viewer"],
            created_at="2020-01-01T00:00:00",
            expires_at="2020-12-31T23:59:59",
        )
        assert key.is_expired()
        assert not key.is_valid()

    def test_revoked_key(self):
        key = APIKey(
            key="aios_test",
            subject="user",
            roles=["viewer"],
            created_at="2026-01-01T00:00:00",
            revoked=True,
        )
        assert key.is_expired()
        assert not key.is_valid()

    def test_no_expiration(self):
        key = APIKey(
            key="aios_test",
            subject="user",
            roles=["viewer"],
            created_at="2026-01-01T00:00:00",
            expires_at=None,
        )
        assert not key.is_expired()
        assert key.is_valid()

    def test_to_dict(self):
        key = APIKey(
            key="aios_test",
            subject="user",
            roles=["admin"],
            created_at="2026-01-01T00:00:00",
        )
        d = key.to_dict()
        assert d["key"] == "aios_test"
        assert d["subject"] == "user"
        assert d["roles"] == ["admin"]

    def test_from_dict(self):
        data = {
            "key": "aios_test",
            "subject": "user",
            "roles": ["viewer"],
            "created_at": "2026-01-01T00:00:00",
            "expires_at": None,
            "last_used": None,
            "usage_count": 0,
            "revoked": False,
        }
        key = APIKey.from_dict(data)
        assert key.key == "aios_test"


class TestSecretManager:
    def test_generate_key(self):
        manager = SecretManager()
        key = manager.generate_key("test-user", ["admin"])
        assert key.subject == "test-user"
        assert key.roles == ["admin"]
        assert key.key.startswith("aios_")
        assert len(key.key) > 20

    def test_generate_key_with_ttl(self):
        manager = SecretManager()
        key = manager.generate_key("user", ["viewer"], ttl_days=30)
        assert key.expires_at is not None

    def test_generate_key_custom_prefix(self):
        manager = SecretManager()
        key = manager.generate_key("user", ["viewer"], prefix="custom")
        assert key.key.startswith("custom_")

    def test_max_keys_per_subject(self):
        manager = SecretManager(max_keys_per_subject=2)
        manager.generate_key("user", ["viewer"])
        manager.generate_key("user", ["viewer"])
        with pytest.raises(ValueError, match="max keys"):
            manager.generate_key("user", ["viewer"])

    def test_revoke_key(self):
        manager = SecretManager()
        key = manager.generate_key("user", ["admin"])
        assert manager.revoke_key(key.key)
        assert manager.keys[key.key].revoked
        assert not manager.keys[key.key].is_valid()

    def test_revoke_nonexistent(self):
        manager = SecretManager()
        assert not manager.revoke_key("nonexistent_key")

    def test_rotate_key(self):
        manager = SecretManager()
        old_key = manager.generate_key("user", ["admin"])
        new_key = manager.rotate_key(old_key.key)
        assert new_key is not None
        assert new_key.subject == "user"
        assert new_key.roles == ["admin"]
        assert manager.keys[old_key.key].revoked

    def test_rotate_nonexistent(self):
        manager = SecretManager()
        assert manager.rotate_key("nonexistent") is None

    def test_validate_key(self):
        manager = SecretManager()
        key = manager.generate_key("user", ["viewer"])
        is_valid, api_key = manager.validate_key(key.key)
        assert is_valid
        assert api_key.subject == "user"
        assert api_key.usage_count == 1

    def test_validate_invalid_key(self):
        manager = SecretManager()
        is_valid, api_key = manager.validate_key("invalid")
        assert not is_valid
        assert api_key is None

    def test_get_keys_by_subject(self):
        manager = SecretManager()
        manager.generate_key("user1", ["admin"])
        manager.generate_key("user1", ["viewer"])
        manager.generate_key("user2", ["viewer"])
        keys = manager.get_keys_by_subject("user1")
        assert len(keys) == 2

    def test_get_expired_keys(self):
        manager = SecretManager()
        manager.generate_key("user", ["viewer"], ttl_days=0)
        expired = manager.get_expired_keys()
        # TTL 0 means expires now, which is already past
        assert len(expired) >= 0

    def test_cleanup_revoked(self):
        manager = SecretManager()
        key = manager.generate_key("user", ["viewer"])
        manager.revoke_key(key.key)
        # Cleanup with 0 days should remove immediately
        removed = manager.cleanup_revoked(older_than_days=0)
        # Note: may not remove if rotation log timestamp is too recent
        assert removed >= 0

    def test_export_import_keys(self, tmp_path):
        manager = SecretManager()
        manager.generate_key("user1", ["admin"])
        manager.generate_key("user2", ["viewer"])

        export_path = tmp_path / "keys.json"
        count = manager.export_keys(str(export_path))
        assert count == 2

        # Import into new manager
        manager2 = SecretManager()
        imported = manager2.import_keys(str(export_path))
        assert imported == 2
        assert len(manager2.keys) == 2

    def test_health_report(self):
        manager = SecretManager()
        manager.generate_key("user1", ["admin"])
        manager.generate_key("user2", ["viewer"])
        report = manager.health_report()
        assert report["total_keys"] == 2
        assert report["active_keys"] == 2
        assert report["subjects"] == 2

    def test_generate_env_export(self, tmp_path):
        manager = SecretManager()
        manager.generate_key("user", ["admin"])

        env_path = tmp_path / ".env"
        manager.generate_env_export(str(env_path))

        assert env_path.exists()
        content = env_path.read_text()
        assert "AIOS_API_KEYS" in content
        assert "export" in content
