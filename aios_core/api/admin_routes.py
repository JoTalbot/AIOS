"""AIOS Admin API Routes

Endpoints for:
- Data export/import
- Secret/key management
- Backup operations

These endpoints require 'admin' role.
"""

import logging
import os
import sqlite3
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from aios_core.backup_manager import BackupManager

# Import our new modules
from aios_core.data_export import DataExporter, DataImporter
from aios_core.secret_manager import SecretManager
from aios_core.storage import Database
from aios_core.webhook_manager import WebhookManager

# Global instances (initialized in create_routes)
_secret_manager: SecretManager | None = None
_backup_manager: BackupManager | None = None
_webhook_manager: WebhookManager | None = None
_db_path: str = "aios.sqlite"
logger = logging.getLogger(__name__)


def init_admin_routes(
    db_path: str = "aios.sqlite", backup_dir: str = "./backups"
) -> None:
    """Initialize admin route handlers with database path."""
    global _db_path, _secret_manager, _backup_manager, _webhook_manager
    _db_path = db_path
    # Initialise only a new/empty database. Existing installations can have a
    # deliberately partial or legacy schema and must not be mutated here.
    needs_schema = not Path(db_path).exists()
    if not needs_schema:
        with sqlite3.connect(db_path) as conn:
            needs_schema = (
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1"
                ).fetchone()
                is None
            )
    if needs_schema:
        Database(db_path=db_path).close()
    _secret_manager = SecretManager()
    _backup_manager = BackupManager(db_path=db_path, backup_dir=backup_dir)
    _webhook_manager = WebhookManager()


def _validated_data_path(raw_path: object, *, must_exist: bool = False) -> str:
    """Validate an admin import/export path against optional operator root.

    Set ``AIOS_ADMIN_DATA_DIR`` in production to confine file operations to a
    dedicated directory. Leaving it unset preserves local development and
    existing CLI behaviour while still rejecting invalid path values.
    """
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("A non-empty file path is required")
    path = Path(raw_path).expanduser()
    try:
        resolved = path.resolve(strict=must_exist)
    except OSError as exc:
        raise ValueError("File path does not exist or is not accessible") from exc
    base_dir = os.environ.get("AIOS_ADMIN_DATA_DIR")
    if base_dir:
        base = Path(base_dir).expanduser().resolve(strict=False)
        if not resolved.is_relative_to(base):
            raise ValueError("Path must be inside AIOS_ADMIN_DATA_DIR")
    return str(resolved)


def _require_admin(request: Request):
    """Check if user has admin role."""
    try:
        principal = request.state.principal
        if not principal or "admin" not in principal.roles:
            raise HTTPException(403, "Admin role required")
    except AttributeError as err:
        raise HTTPException(401, "Authentication required") from err


# ============================================================
# Data Export/Import Endpoints
# ============================================================


async def export_data(request: Request) -> None:
    """Export data from AIOS.

    POST /api/v1/admin/export
    Body: {
        "type": "tasks|memory|audit|knowledge|all",
        "format": "json|csv",
        "output": "/path/to/output",
        "since": "2026-01-01",  # optional
        "limit": 1000  # optional
    }
    """
    _require_admin(request)
    body = await request.json()

    export_type = body.get("type", "all")
    format_type = body.get("format", "json")
    try:
        output_path = _validated_data_path(body.get("output", "./export"))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    since = body.get("since")
    limit = body.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
            if not 1 <= limit <= 100_000:
                raise ValueError
        except (TypeError, ValueError):
            return JSONResponse({"error": "limit must be an integer between 1 and 100000"}, status_code=400)

    try:
        with DataExporter(_db_path) as exporter:
            if export_type == "all":
                counts = exporter.export_all(output_path, format_type, since)
                return JSONResponse(
                    {
                        "status": "success",
                        "type": "all",
                        "format": format_type,
                        "output": output_path,
                        "counts": counts,
                    }
                )
            elif export_type == "tasks":
                count = exporter.export_tasks(
                    output_path, format_type, limit, since=since
                )
            elif export_type == "memory":
                count = exporter.export_memory(output_path, format_type, limit)
            elif export_type == "audit":
                count = exporter.export_audit_log(output_path, format_type, since=since)
            elif export_type == "knowledge":
                count = exporter.export_knowledge_graph(output_path, format_type)
            else:
                return JSONResponse(
                    {"error": f"Unknown type: {export_type}"}, status_code=400
                )

            return JSONResponse(
                {
                    "status": "success",
                    "type": export_type,
                    "format": format_type,
                    "output": output_path,
                    "count": count,
                }
            )
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


async def import_data(request: Request) -> None:
    """Import data into AIOS.

    POST /api/v1/admin/import
    Body: {
        "type": "tasks",
        "format": "json|csv",
        "input": "/path/to/input"
    }
    """
    _require_admin(request)
    body = await request.json()

    import_type = body.get("type", "tasks")
    format_type = body.get("format", "json")
    input_path = body.get("input")

    try:
        input_path = _validated_data_path(input_path, must_exist=True)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if import_type != "tasks":
        return JSONResponse({"error": "Only tasks import is supported"}, status_code=400)
    if format_type not in {"json", "csv"}:
        return JSONResponse({"error": "Unsupported format"}, status_code=400)

    try:
        with DataImporter(_db_path) as importer:
            count = importer.import_tasks(input_path, format_type)
            return JSONResponse(
                {
                    "status": "success",
                    "type": import_type,
                    "format": format_type,
                    "count": count,
                }
            )
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


# ============================================================
# Secret Management Endpoints
# ============================================================


async def generate_api_key(request: Request) -> None:
    """Generate a new API key.

    POST /api/v1/admin/keys/generate
    Body: {
        "subject": "user-name",
        "roles": ["admin", "viewer"],
        "ttl_days": 90,  # optional
        "prefix": "aios"  # optional
    }
    """
    _require_admin(request)
    body = await request.json()

    subject = body.get("subject")
    roles = body.get("roles", ["viewer"])
    ttl_days = body.get("ttl_days")
    prefix = body.get("prefix", "aios")

    if not subject:
        return JSONResponse({"error": "subject required"}, status_code=400)

    try:
        key = _secret_manager.generate_key(subject, roles, ttl_days, prefix)
        return JSONResponse(
            {
                "status": "success",
                "key": key.key,
                "subject": key.subject,
                "roles": key.roles,
                "expires_at": key.expires_at,
                "created_at": key.created_at,
            }
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


async def list_api_keys(request: Request) -> None:
    """List all API keys.

    GET /api/v1/admin/keys
    """
    _require_admin(request)
    subject_filter = request.query_params.get("subject")

    keys = _secret_manager.keys.values()
    if subject_filter:
        keys = [k for k in keys if k.subject == subject_filter]

    return JSONResponse(
        {
            "keys": [
                {
                    "key_prefix": k.key[:16] + "...",
                    "subject": k.subject,
                    "roles": k.roles,
                    "created_at": k.created_at,
                    "expires_at": k.expires_at,
                    "is_valid": k.is_valid(),
                    "usage_count": k.usage_count,
                    "last_used": k.last_used,
                }
                for k in keys
            ],
            "total": len(list(keys)),
        }
    )


async def revoke_api_key(request: Request) -> None:
    """Revoke an API key.

    POST /api/v1/admin/keys/revoke
    Body: {
        "key": "full-api-key-string",
        "reason": "compromised"
    }
    """
    _require_admin(request)
    body = await request.json()

    key = body.get("key")
    reason = body.get("reason", "")

    if not key:
        return JSONResponse({"error": "key required"}, status_code=400)

    success = _secret_manager.revoke_key(key, reason)
    if success:
        return JSONResponse({"status": "success", "message": "Key revoked"})
    else:
        return JSONResponse({"error": "Key not found"}, status_code=404)


async def rotate_api_key(request: Request) -> None:
    """Rotate an API key.

    POST /api/v1/admin/keys/rotate
    Body: {
        "old_key": "full-api-key-string",
        "ttl_days": 90,
        "reason": "scheduled rotation"
    }
    """
    _require_admin(request)
    body = await request.json()

    old_key = body.get("old_key")
    ttl_days = body.get("ttl_days")
    reason = body.get("reason", "rotation")

    if not old_key:
        return JSONResponse({"error": "old_key required"}, status_code=400)

    new_key = _secret_manager.rotate_key(old_key, ttl_days, reason)
    if new_key:
        return JSONResponse(
            {
                "status": "success",
                "new_key": new_key.key,
                "subject": new_key.subject,
                "roles": new_key.roles,
                "expires_at": new_key.expires_at,
                "message": "Old key revoked, new key generated",
            }
        )
    else:
        return JSONResponse({"error": "Old key not found"}, status_code=404)


async def keys_health(request: Request) -> None:
    """Get API keys health report.

    GET /api/v1/admin/keys/health
    """
    _require_admin(request)
    report = _secret_manager.health_report()
    return JSONResponse(report)


async def export_keys(request: Request) -> None:
    """Export API keys to file.

    POST /api/v1/admin/keys/export
    Body: {
        "path": "/path/to/keys_backup.json"
    }
    """
    _require_admin(request)
    body = await request.json()
    path = body.get("path", "keys_backup.json")

    try:
        count = _secret_manager.export_keys(path)
        return JSONResponse(
            {
                "status": "success",
                "path": path,
                "count": count,
            }
        )
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


async def generate_env_file(request: Request) -> None:
    """Generate AIOS_API_KEYS env file.

    POST /api/v1/admin/keys/env
    Body: {
        "path": ".env"
    }
    """
    _require_admin(request)
    body = await request.json()
    path = body.get("path", ".env")

    try:
        _secret_manager.generate_env_export(path)
        return JSONResponse(
            {
                "status": "success",
                "path": path,
                "message": "Environment file generated",
            }
        )
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


# ============================================================
# Backup Management Endpoints
# ============================================================


async def create_backup(request: Request) -> None:
    """Create a database backup.

    POST /api/v1/admin/backups
    Body: {
        "label": "pre-deploy",  # optional
        "mode": "full"  # optional
    }
    """
    _require_admin(request)
    body = await request.json()

    label = body.get("label", "")
    mode = body.get("mode", "full")

    try:
        metadata = _backup_manager.create_backup(mode, label)
        return JSONResponse(
            {
                "status": "success",
                "backup_id": metadata.backup_id,
                "size_bytes": metadata.size_bytes,
                "checksum": metadata.checksum,
                "compressed": metadata.compressed,
                "tables": metadata.tables,
                "row_counts": metadata.row_counts,
                "created_at": metadata.created_at,
            }
        )
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


async def list_backups(request: Request) -> None:
    """List all backups.

    GET /api/v1/admin/backups
    """
    _require_admin(request)
    backups = _backup_manager.list_backups()
    return JSONResponse(
        {
            "backups": [
                {
                    "backup_id": b.backup_id,
                    "created_at": b.created_at,
                    "size_bytes": b.size_bytes,
                    "size_mb": round(b.size_bytes / 1024 / 1024, 2),
                    "checksum": b.checksum[:16] + "...",
                    "compressed": b.compressed,
                    "mode": b.mode,
                    "tables": b.tables,
                }
                for b in backups
            ],
            "total": len(backups),
        }
    )


async def verify_backup(request: Request) -> None:
    """Verify backup integrity.

    POST /api/v1/admin/backups/verify
    Body: {
        "backup_id": "backup_20260723_120000"
    }
    """
    _require_admin(request)
    body = await request.json()
    backup_id = body.get("backup_id")

    if not backup_id:
        return JSONResponse({"error": "backup_id required"}, status_code=400)

    is_valid = _backup_manager.verify_backup(backup_id)
    return JSONResponse(
        {
            "backup_id": backup_id,
            "valid": is_valid,
            "status": "healthy" if is_valid else "corrupted",
        }
    )


async def restore_backup(request: Request) -> None:
    """Restore database from backup.

    POST /api/v1/admin/backups/restore
    Body: {
        "backup_id": "backup_20260723_120000",
        "target": "/path/to/target.sqlite"  # optional
    }
    """
    _require_admin(request)
    body = await request.json()

    backup_id = body.get("backup_id")
    target = body.get("target")

    if not backup_id:
        return JSONResponse({"error": "backup_id required"}, status_code=400)

    success = _backup_manager.restore_backup(backup_id, target)
    if success:
        return JSONResponse(
            {
                "status": "success",
                "backup_id": backup_id,
                "target": target or _db_path,
                "message": "Database restored successfully",
            }
        )
    else:
        return JSONResponse({"error": "Restore failed"}, status_code=500)


async def cleanup_backups(request: Request) -> None:
    """Remove old backups.

    POST /api/v1/admin/backups/cleanup
    """
    _require_admin(request)
    removed = _backup_manager.cleanup_old_backups()
    return JSONResponse(
        {
            "status": "success",
            "removed": removed,
            "remaining": len(_backup_manager.backups),
        }
    )


async def backups_health(request: Request) -> None:
    """Get backups health report.

    GET /api/v1/admin/backups/health
    """
    _require_admin(request)
    report = _backup_manager.health_report()
    schedule = _backup_manager.schedule_info()
    return JSONResponse(
        {
            "health": report,
            "schedule": schedule,
        }
    )


# ============================================================
# Webhook Management Endpoints
# ============================================================


async def register_webhook(request: Request) -> None:
    """Register a new webhook target.

    POST /api/v1/admin/webhooks
    Body: {
        "name": "slack-alerts",
        "url": "https://hooks.slack.com/...",
        "events": ["ban_detected", "low_success_rate"],
        "secret": "optional-hmac-secret",
        "headers": {"X-Custom": "value"}
    }
    """
    _require_admin(request)
    body = await request.json()

    name = body.get("name")
    url = body.get("url")
    events = body.get("events", [])
    secret = body.get("secret")
    headers = body.get("headers", {})

    if not name or not url or not events:
        return JSONResponse({"error": "name, url, events required"}, status_code=400)

    try:
        target = _webhook_manager.register(name, url, events, secret, headers)
        return JSONResponse(
            {
                "status": "success",
                "webhook": target.to_dict(),
            }
        )
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


async def list_webhooks(request: Request) -> None:
    """List all webhook targets.

    GET /api/v1/admin/webhooks
    """
    _require_admin(request)
    targets = _webhook_manager.list_targets()
    return JSONResponse(
        {
            "webhooks": targets,
            "total": len(targets),
        }
    )


async def unregister_webhook(request: Request) -> None:
    """Remove a webhook target.

    DELETE /api/v1/admin/webhooks
    Body: {
        "name": "slack-alerts"
    }
    """
    _require_admin(request)
    body = await request.json()
    name = body.get("name")

    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)

    success = _webhook_manager.unregister(name)
    if success:
        return JSONResponse(
            {"status": "success", "message": f"Webhook '{name}' removed"}
        )
    return JSONResponse({"error": "Webhook not found"}, status_code=404)


async def toggle_webhook(request: Request) -> None:
    """Activate or deactivate a webhook.

    POST /api/v1/admin/webhooks/toggle
    Body: {
        "name": "slack-alerts",
        "active": true
    }
    """
    _require_admin(request)
    body = await request.json()
    name = body.get("name")
    active = body.get("active", True)

    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)

    success = _webhook_manager.activate(name) if active else _webhook_manager.deactivate(name)

    if success:
        return JSONResponse(
            {
                "status": "success",
                "name": name,
                "active": active,
            }
        )
    return JSONResponse({"error": "Webhook not found"}, status_code=404)


async def test_webhook(request: Request) -> None:
    """Send a test notification to a webhook.

    POST /api/v1/admin/webhooks/test
    Body: {
        "name": "slack-alerts"
    }
    """
    _require_admin(request)
    body = await request.json()
    name = body.get("name")

    if not name:
        return JSONResponse({"error": "name required"}, status_code=400)

    result = _webhook_manager.test_webhook(name)
    return JSONResponse(result)


async def webhook_history(request: Request) -> None:
    """Get webhook notification history.

    GET /api/v1/admin/webhooks/history?event=ban_detected&limit=50
    """
    _require_admin(request)
    event = request.query_params.get("event")
    limit = int(request.query_params.get("limit", "50"))

    history = _webhook_manager.get_history(event=event, limit=limit)
    return JSONResponse(
        {
            "history": history,
            "total": len(history),
            "filter_event": event,
        }
    )


async def send_webhook_event(request: Request) -> None:
    """Send a custom webhook event.

    POST /api/v1/admin/webhooks/notify
    Body: {
        "event": "custom",
        "data": {"message": "Hello"},
        "severity": "info"
    }
    """
    _require_admin(request)
    body = await request.json()

    event = body.get("event", "custom")
    data = body.get("data", {})
    severity = body.get("severity", "info")

    result = _webhook_manager.notify(event, data, severity=severity)
    return JSONResponse(result)


async def webhooks_health(request: Request) -> None:
    """Get webhook system health report.

    GET /api/v1/admin/webhooks/health
    """
    _require_admin(request)
    report = _webhook_manager.health_report()
    return JSONResponse(report)


async def export_webhooks(request: Request) -> None:
    """Export webhook configuration.

    POST /api/v1/admin/webhooks/export
    Body: {
        "path": "/path/to/webhooks.json"
    }
    """
    _require_admin(request)
    body = await request.json()
    path = body.get("path", "webhooks_config.json")

    try:
        count = _webhook_manager.export_config(path)
        return JSONResponse(
            {
                "status": "success",
                "path": path,
                "count": count,
            }
        )
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


async def import_webhooks(request: Request) -> None:
    """Import webhook configuration.

    POST /api/v1/admin/webhooks/import
    Body: {
        "path": "/path/to/webhooks.json"
    }
    """
    _require_admin(request)
    body = await request.json()
    path = body.get("path")

    if not path:
        return JSONResponse({"error": "path required"}, status_code=400)

    try:
        count = _webhook_manager.import_config(path)
        return JSONResponse(
            {
                "status": "success",
                "path": path,
                "count": count,
            }
        )
    except Exception as e:
        logger.exception("Admin API operation failed")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


# ============================================================
# Route Definitions
# ============================================================


def get_admin_routes():
    """Return admin API routes."""
    return [
        # Data Export/Import
        Route("/api/v1/admin/export", export_data, methods=["POST"]),
        Route("/api/v1/admin/import", import_data, methods=["POST"]),
        # Secret Management
        Route("/api/v1/admin/keys/generate", generate_api_key, methods=["POST"]),
        Route("/api/v1/admin/keys", list_api_keys, methods=["GET"]),
        Route("/api/v1/admin/keys/revoke", revoke_api_key, methods=["POST"]),
        Route("/api/v1/admin/keys/rotate", rotate_api_key, methods=["POST"]),
        Route("/api/v1/admin/keys/health", keys_health, methods=["GET"]),
        Route("/api/v1/admin/keys/export", export_keys, methods=["POST"]),
        Route("/api/v1/admin/keys/env", generate_env_file, methods=["POST"]),
        # Backup Management
        Route("/api/v1/admin/backups", create_backup, methods=["POST"]),
        Route("/api/v1/admin/backups/list", list_backups, methods=["GET"]),
        Route("/api/v1/admin/backups/verify", verify_backup, methods=["POST"]),
        Route("/api/v1/admin/backups/restore", restore_backup, methods=["POST"]),
        Route("/api/v1/admin/backups/cleanup", cleanup_backups, methods=["POST"]),
        Route("/api/v1/admin/backups/health", backups_health, methods=["GET"]),
        # Webhook Management
        Route("/api/v1/admin/webhooks", register_webhook, methods=["POST"]),
        Route("/api/v1/admin/webhooks/list", list_webhooks, methods=["GET"]),
        Route(
            "/api/v1/admin/webhooks/unregister",
            unregister_webhook,
            methods=["DELETE", "POST"],
        ),
        Route("/api/v1/admin/webhooks/toggle", toggle_webhook, methods=["POST"]),
        Route("/api/v1/admin/webhooks/test", test_webhook, methods=["POST"]),
        Route("/api/v1/admin/webhooks/history", webhook_history, methods=["GET"]),
        Route("/api/v1/admin/webhooks/notify", send_webhook_event, methods=["POST"]),
        Route("/api/v1/admin/webhooks/health", webhooks_health, methods=["GET"]),
        Route("/api/v1/admin/webhooks/export", export_webhooks, methods=["POST"]),
        Route("/api/v1/admin/webhooks/import", import_webhooks, methods=["POST"]),
    ]
