"""Tests for AIOS admin API routes."""

import json
import pytest
import sqlite3
import tempfile
from pathlib import Path
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from aios_core.api.admin_routes import (
    init_admin_routes,
    get_admin_routes,
    _secret_manager,
    _backup_manager,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, status TEXT, created_at TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE personal_memory (id TEXT PRIMARY KEY, owner TEXT, content TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE audit_log (id TEXT PRIMARY KEY, event_type TEXT, timestamp TEXT, details TEXT)")
    conn.execute("CREATE TABLE knowledge_graph (id TEXT PRIMARY KEY, subject TEXT, predicate TEXT, object TEXT, created_at TEXT)")
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


@pytest.fixture
def client(admin_app):
    """Create test client."""
    return TestClient(admin_app)


class TestDataExportAPI:
    def test_export_tasks(self, client, tmp_path):
        output = tmp_path / "tasks.json"
        response = client.post("/api/v1/admin/export", json={
            "type": "tasks",
            "format": "json",
            "output": str(output),
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1

    def test_export_all(self, client, tmp_path):
        output_dir = tmp_path / "export"
        response = client.post("/api/v1/admin/export", json={
            "type": "all",
            "format": "json",
            "output": str(output_dir),
        })
        assert response.status_code == 200
        data = response.json()
        assert "counts" in data


class TestSecretsAPI:
    def test_generate_key(self, client):
        response = client.post("/api/v1/admin/keys/generate", json={
            "subject": "test-user",
            "roles": ["admin", "viewer"],
            "ttl_days": 30,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["subject"] == "test-user"
        assert "key" in data
        assert data["key"].startswith("aios_")

    def test_list_keys(self, client):
        # Generate a key first
        client.post("/api/v1/admin/keys/generate", json={
            "subject": "user1",
            "roles": ["viewer"],
        })

        response = client.get("/api/v1/admin/keys")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_revoke_key(self, client):
        # Generate a key
        gen_response = client.post("/api/v1/admin/keys/generate", json={
            "subject": "user1",
            "roles": ["viewer"],
        })
        key = gen_response.json()["key"]

        # Revoke it
        response = client.post("/api/v1/admin/keys/revoke", json={
            "key": key,
            "reason": "test revocation",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_rotate_key(self, client):
        # Generate a key
        gen_response = client.post("/api/v1/admin/keys/generate", json={
            "subject": "user1",
            "roles": ["admin"],
        })
        old_key = gen_response.json()["key"]

        # Rotate it
        response = client.post("/api/v1/admin/keys/rotate", json={
            "old_key": old_key,
            "ttl_days": 60,
            "reason": "test rotation",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "new_key" in data
        assert data["new_key"] != old_key

    def test_keys_health(self, client):
        response = client.get("/api/v1/admin/keys/health")
        assert response.status_code == 200
        data = response.json()
        assert "total_keys" in data
        assert "active_keys" in data


class TestBackupAPI:
    def test_create_backup(self, client):
        response = client.post("/api/v1/admin/backups", json={
            "label": "test-backup",
            "mode": "full",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "backup_id" in data
        assert data["size_bytes"] > 0

    def test_list_backups(self, client):
        # Create a backup first
        client.post("/api/v1/admin/backups", json={"label": "test"})

        response = client.get("/api/v1/admin/backups/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_verify_backup(self, client):
        # Create a backup
        create_response = client.post("/api/v1/admin/backups", json={"label": "verify-test"})
        backup_id = create_response.json()["backup_id"]

        # Verify it
        response = client.post("/api/v1/admin/backups/verify", json={
            "backup_id": backup_id,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_restore_backup(self, client, tmp_path):
        # Create a backup
        create_response = client.post("/api/v1/admin/backups", json={"label": "restore-test"})
        backup_id = create_response.json()["backup_id"]

        # Restore to new location
        target = tmp_path / "restored.sqlite"
        response = client.post("/api/v1/admin/backups/restore", json={
            "backup_id": backup_id,
            "target": str(target),
        })
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert target.exists()

    def test_cleanup_backups(self, client):
        # Create some backups
        for i in range(3):
            client.post("/api/v1/admin/backups", json={"label": f"cleanup-{i}"})

        response = client.post("/api/v1/admin/backups/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert "removed" in data
        assert "remaining" in data

    def test_backups_health(self, client):
        response = client.get("/api/v1/admin/backups/health")
        assert response.status_code == 200
        data = response.json()
        assert "health" in data
        assert "schedule" in data
