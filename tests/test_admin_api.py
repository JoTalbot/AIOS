"""Tests for AIOS admin API routes."""

import json
import sqlite3
import tempfile
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from aios_core.api.admin_routes import (
    _backup_manager,
    _secret_manager,
    _webhook_manager,
    get_admin_routes,
    init_admin_routes,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, status TEXT, created_at TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE personal_memory (id TEXT PRIMARY KEY, owner TEXT, content TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE audit_log (id TEXT PRIMARY KEY, event_type TEXT, timestamp TEXT, details TEXT)"
    )
    conn.execute(
        "CREATE TABLE knowledge_graph (id TEXT PRIMARY KEY, subject TEXT, predicate TEXT, object TEXT, created_at TEXT)"
    )
    conn.execute("INSERT INTO tasks VALUES ('t1', 'done', '2026-01-01', '2026-01-02')")
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def mock_principal():
    """Create a mock principal with admin role."""

    class Principal:
        def __init__(self):
            self.subject = "admin-user"
            self.roles = ["admin"]

    return Principal()


@pytest.fixture
def admin_app(test_db, tmp_path, mock_principal):
    """Create a test app with admin routes."""
    backup_dir = tmp_path / "backups"
    init_admin_routes(db_path=test_db, backup_dir=str(backup_dir))

    # Middleware to inject principal
    from starlette.middleware.base import BaseHTTPMiddleware

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request.state.principal = mock_principal
            response = await call_next(request)
            return response

    app = Starlette(routes=get_admin_routes())
    app.add_middleware(AuthMiddleware)
    return app


@pytest_asyncio.fixture
async def client(admin_app):
    """Create async test client via httpx ASGITransport."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=admin_app),
        base_url="http://testserver",
    ) as c:
        yield c


@pytest.mark.asyncio
class TestDataExportAPI:
    async def test_export_tasks(self, client, tmp_path):
        output = tmp_path / "tasks.json"
        response = await client.post(
            "/api/v1/admin/export",
            json={
                "type": "tasks",
                "format": "json",
                "output": str(output),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_export_all(self, client, tmp_path):
        output_dir = tmp_path / "export"
        response = await client.post(
            "/api/v1/admin/export",
            json={
                "type": "all",
                "format": "json",
                "output": str(output_dir),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "counts" in data


@pytest.mark.asyncio
class TestSecretsAPI:
    async def test_generate_key(self, client):
        response = await client.post(
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
        assert data["subject"] == "test-user"
        assert "key" in data
        assert data["key"].startswith("aios_")

    @pytest.mark.asyncio
    async def test_list_keys(self, client):
        # Generate a key first
        await client.post(
            "/api/v1/admin/keys/generate",
            json={
                "subject": "user1",
                "roles": ["viewer"],
            },
        )

        response = await client.get("/api/v1/admin/keys")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_revoke_key(self, client):
        # Generate a key
        gen_response = await client.post(
            "/api/v1/admin/keys/generate",
            json={
                "subject": "user1",
                "roles": ["viewer"],
            },
        )
        key = gen_response.json()["key"]

        # Revoke it
        response = await client.post(
            "/api/v1/admin/keys/revoke",
            json={
                "key": key,
                "reason": "test revocation",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_rotate_key(self, client):
        # Generate a key
        gen_response = await client.post(
            "/api/v1/admin/keys/generate",
            json={
                "subject": "user1",
                "roles": ["admin"],
            },
        )
        old_key = gen_response.json()["key"]

        # Rotate it
        response = await client.post(
            "/api/v1/admin/keys/rotate",
            json={
                "old_key": old_key,
                "ttl_days": 60,
                "reason": "test rotation",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "new_key" in data
        assert data["new_key"] != old_key

    @pytest.mark.asyncio
    async def test_keys_health(self, client):
        response = await client.get("/api/v1/admin/keys/health")
        assert response.status_code == 200
        data = response.json()
        assert "total_keys" in data
        assert "active_keys" in data


@pytest.mark.asyncio
class TestBackupAPI:
    async def test_create_backup(self, client):
        response = await client.post(
            "/api/v1/admin/backups",
            json={
                "label": "test-backup",
                "mode": "full",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "backup_id" in data
        assert data["size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_list_backups(self, client):
        # Create a backup first
        await client.post("/api/v1/admin/backups", json={"label": "test"})

        response = await client.get("/api/v1/admin/backups/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_verify_backup(self, client):
        # Create a backup
        create_response = await client.post("/api/v1/admin/backups", json={"label": "verify-test"})
        backup_id = create_response.json()["backup_id"]

        # Verify it
        response = await client.post(
            "/api/v1/admin/backups/verify",
            json={
                "backup_id": backup_id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_restore_backup(self, client, tmp_path):
        # Create a backup
        create_response = await client.post("/api/v1/admin/backups", json={"label": "restore-test"})
        backup_id = create_response.json()["backup_id"]

        # Restore to new location
        target = tmp_path / "restored.sqlite"
        response = await client.post(
            "/api/v1/admin/backups/restore",
            json={
                "backup_id": backup_id,
                "target": str(target),
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert target.exists()

    @pytest.mark.asyncio
    async def test_cleanup_backups(self, client):
        # Create some backups
        for i in range(3):
            await client.post("/api/v1/admin/backups", json={"label": f"cleanup-{i}"})

        response = await client.post("/api/v1/admin/backups/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert "removed" in data
        assert "remaining" in data

    @pytest.mark.asyncio
    async def test_backups_health(self, client):
        response = await client.get("/api/v1/admin/backups/health")
        assert response.status_code == 200
        data = response.json()
        assert "health" in data
        assert "schedule" in data


@pytest.mark.asyncio
class TestWebhooksAPI:
    async def test_register_webhook(self, client):
        response = await client.post(
            "/api/v1/admin/webhooks",
            json={
                "name": "slack-alerts",
                "url": "https://hooks.slack.com/test",
                "events": ["ban_detected", "low_success_rate"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["webhook"]["name"] == "slack-alerts"

    @pytest.mark.asyncio
    async def test_list_webhooks(self, client):
        # Register a webhook first
        await client.post(
            "/api/v1/admin/webhooks",
            json={
                "name": "test-hook",
                "url": "https://example.com/hook",
                "events": ["ban_detected"],
            },
        )

        response = await client.get("/api/v1/admin/webhooks/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_toggle_webhook(self, client):
        # Register
        await client.post(
            "/api/v1/admin/webhooks",
            json={
                "name": "toggle-test",
                "url": "https://example.com/hook",
                "events": ["ban_detected"],
            },
        )

        # Deactivate
        response = await client.post(
            "/api/v1/admin/webhooks/toggle",
            json={
                "name": "toggle-test",
                "active": False,
            },
        )
        assert response.status_code == 200
        assert not response.json()["active"]

    @pytest.mark.asyncio
    async def test_test_webhook(self, client):
        await client.post(
            "/api/v1/admin/webhooks",
            json={
                "name": "test-hook",
                "url": "https://example.com/hook",
                "events": ["custom"],
            },
        )

        response = await client.post(
            "/api/v1/admin/webhooks/test",
            json={
                "name": "test-hook",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "test_sent"

    @pytest.mark.asyncio
    async def test_send_webhook_event(self, client):
        await client.post(
            "/api/v1/admin/webhooks",
            json={
                "name": "event-hook",
                "url": "https://example.com/hook",
                "events": ["custom"],
            },
        )

        response = await client.post(
            "/api/v1/admin/webhooks/notify",
            json={
                "event": "custom",
                "data": {"message": "Hello"},
                "severity": "info",
            },
        )
        assert response.status_code == 200
        assert response.json()["targets_triggered"] >= 1

    @pytest.mark.asyncio
    async def test_webhook_history(self, client):
        await client.post(
            "/api/v1/admin/webhooks",
            json={
                "name": "history-hook",
                "url": "https://example.com/hook",
                "events": ["ban_detected"],
            },
        )

        # Send some events
        await client.post(
            "/api/v1/admin/webhooks/notify",
            json={
                "event": "ban_detected",
                "data": {"profile": "test"},
            },
        )

        response = await client.get("/api/v1/admin/webhooks/history")
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_webhooks_health(self, client):
        response = await client.get("/api/v1/admin/webhooks/health")
        assert response.status_code == 200
        data = response.json()
        assert "total_targets" in data
        assert "active_targets" in data
