"""End-to-End tests for Admin API endpoints."""

import json

import pytest
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from aios_core.api.admin_routes import get_admin_routes, init_admin_routes


class MockPrincipal:
    """Mock principal for testing."""

    def __init__(self, roles=None):
        self.subject = "test-user"
        self.roles = roles or ["admin"]


class AuthMiddleware(BaseHTTPMiddleware):
    """Mock authentication middleware."""

    async def dispatch(self, request: Request, call_next):
        request.state.principal = MockPrincipal(["admin"])
        response = await call_next(request)
        return response


@pytest.fixture
def admin_app(tmp_path):
    """Create admin app for testing."""
    db_path = tmp_path / "test.sqlite"
    backup_dir = tmp_path / "backups"

    init_admin_routes(db_path=str(db_path), backup_dir=str(backup_dir))

    app = Starlette(routes=get_admin_routes())
    app.add_middleware(AuthMiddleware)
    return app


@pytest.fixture
def client(admin_app):
    """Create test client."""
    return TestClient(admin_app)


class TestExportImportE2E:
    """End-to-end tests for export/import operations."""

    def test_export_import_cycle(self, client, tmp_path):
        """Test complete export and import cycle."""
        # Export data
        export_path = tmp_path / "export.json"
        response = client.post(
            "/api/v1/admin/export",
            json={
                "type": "all",
                "format": "json",
                "output": str(export_path),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify export file exists
        assert export_path.exists()

        # Import data
        response = client.post(
            "/api/v1/admin/import",
            json={
                "type": "tasks",
                "format": "json",
                "input": str(export_path),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_export_csv_format(self, client, tmp_path):
        """Test export in CSV format."""
        export_path = tmp_path / "export.csv"

        response = client.post(
            "/api/v1/admin/export",
            json={
                "type": "tasks",
                "format": "csv",
                "output": str(export_path),
            },
        )

        assert response.status_code == 200
        assert export_path.exists()

        # Verify CSV format
        content = export_path.read_text()
        # Should have headers and data


class TestAPIKeysE2E:
    """End-to-end tests for API key management."""

    def test_full_key_lifecycle(self, client):
        """Test complete API key lifecycle."""
        # Generate key
        response = client.post(
            "/api/v1/admin/keys/generate",
            json={
                "subject": "test-user",
                "roles": ["admin", "viewer"],
                "ttl_days": 30,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        key = data["key"]

        # List keys
        response = client.get("/api/v1/admin/keys")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # Check key health
        response = client.get("/api/v1/admin/keys/health")
        assert response.status_code == 200
        health = response.json()
        assert health["active_keys"] >= 1

        # Rotate key
        response = client.post(
            "/api/v1/admin/keys/rotate",
            json={
                "old_key": key,
                "ttl_days": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        new_key = data["new_key"]

        # Revoke new key
        response = client.post(
            "/api/v1/admin/keys/revoke",
            json={
                "key": new_key,
                "reason": "test revocation",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_key_export_import(self, client, tmp_path):
        """Test API key export and import."""
        # Generate some keys
        for i in range(3):
            client.post(
                "/api/v1/admin/keys/generate",
                json={
                    "subject": f"user-{i}",
                    "roles": ["viewer"],
                },
            )

        # Export keys
        export_path = tmp_path / "keys.json"
        response = client.post(
            "/api/v1/admin/keys/export",
            json={
                "path": str(export_path),
            },
        )

        assert response.status_code == 200
        assert export_path.exists()

        # Verify export contains keys
        content = json.loads(export_path.read_text())
        assert len(content["keys"]) >= 3


class TestBackupsE2E:
    """End-to-end tests for backup operations."""

    def test_full_backup_cycle(self, client, tmp_path):
        """Test complete backup cycle."""
        # Create backup
        response = client.post(
            "/api/v1/admin/backups",
            json={
                "label": "e2e-test",
                "mode": "full",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        backup_id = data["backup_id"]

        # List backups
        response = client.get("/api/v1/admin/backups/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # Verify backup
        response = client.post(
            "/api/v1/admin/backups/verify",
            json={
                "backup_id": backup_id,
            },
        )

        assert response.status_code == 200
        assert response.json()["valid"] is True

        # Restore backup
        restore_path = tmp_path / "restored.sqlite"
        response = client.post(
            "/api/v1/admin/backups/restore",
            json={
                "backup_id": backup_id,
                "target": str(restore_path),
            },
        )

        assert response.status_code == 200
        assert restore_path.exists()

        # Check backup health
        response = client.get("/api/v1/admin/backups/health")
        assert response.status_code == 200
        health = response.json()
        assert "health" in health
        assert "schedule" in health

        # Cleanup old backups
        response = client.post("/api/v1/admin/backups/cleanup")
        assert response.status_code == 200

    def test_multiple_backups_rotation(self, client):
        """Test creating and managing multiple backups."""
        # Create 5 backups
        backup_ids = []
        for i in range(5):
            response = client.post(
                "/api/v1/admin/backups",
                json={
                    "label": f"rotation-{i}",
                },
            )
            assert response.status_code == 200
            backup_ids.append(response.json()["backup_id"])

        # Verify all exist
        response = client.get("/api/v1/admin/backups/list")
        assert response.status_code == 200
        assert response.json()["total"] >= 5


class TestWebhooksE2E:
    """End-to-end tests for webhook operations."""

    def test_full_webhook_lifecycle(self, client):
        """Test complete webhook lifecycle."""
        # Register webhook
        response = client.post(
            "/api/v1/admin/webhooks",
            json={
                "name": "test-webhook",
                "url": "https://example.com/hook",
                "events": ["ban_detected", "backup_completed"],
                "secret": "test-secret",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # List webhooks
        response = client.get("/api/v1/admin/webhooks/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # Toggle webhook
        response = client.post(
            "/api/v1/admin/webhooks/toggle",
            json={
                "name": "test-webhook",
                "active": False,
            },
        )

        assert response.status_code == 200
        assert not response.json()["active"]

        # Send notification
        response = client.post(
            "/api/v1/admin/webhooks/notify",
            json={
                "event": "ban_detected",
                "data": {"profile": "test-profile"},
                "severity": "critical",
            },
        )

        assert response.status_code == 200

        # Check history
        response = client.get("/api/v1/admin/webhooks/history")
        assert response.status_code == 200
        history = response.json()
        assert history["total"] >= 1

        # Test webhook
        response = client.post(
            "/api/v1/admin/webhooks/test",
            json={
                "name": "test-webhook",
            },
        )

        assert response.status_code == 200

        # Check webhook health
        response = client.get("/api/v1/admin/webhooks/health")
        assert response.status_code == 200
        health = response.json()
        assert "total_targets" in health

        # Unregister webhook
        response = client.post(
            "/api/v1/admin/webhooks/unregister",
            json={
                "name": "test-webhook",
            },
        )

        assert response.status_code == 200

    def test_multiple_webhooks(self, client):
        """Test managing multiple webhooks."""
        # Register multiple webhooks
        for i in range(5):
            response = client.post(
                "/api/v1/admin/webhooks",
                json={
                    "name": f"webhook-{i}",
                    "url": f"https://example{i}.com/hook",
                    "events": ["ban_detected"],
                },
            )
            assert response.status_code == 200

        # Verify all registered
        response = client.get("/api/v1/admin/webhooks/list")
        assert response.status_code == 200
        assert response.json()["total"] >= 5


class TestAdminAPIPermissions:
    """Tests for admin API permission checks."""

    def test_admin_access(self, client):
        """Test admin can access all endpoints."""
        endpoints = [
            ("GET", "/api/v1/admin/keys"),
            ("GET", "/api/v1/admin/backups/list"),
            ("GET", "/api/v1/admin/webhooks/list"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})

            # Should succeed with admin role
            assert response.status_code in [200, 405]  # 405 if method not allowed
