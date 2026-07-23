"""AIOS Admin CLI Commands

CLI interface for:
- Data export/import
- API key management
- Database backup/restore

Usage:
    aios admin export --type tasks --format json --output ./export
    aios admin keys generate --subject user1 --roles admin viewer
    aios admin backup create --label pre-deploy
"""

import json
import sys
from pathlib import Path


def run_export(args):
    """Handle 'aios admin export' command."""
    from aios_core.data_export import DataExporter

    export_type = args.type
    format_type = args.format
    output = args.output
    since = getattr(args, "since", None)
    limit = getattr(args, "limit", None)
    db_path = getattr(args, "db", "aios.sqlite")

    try:
        with DataExporter(db_path) as exporter:
            if export_type == "all":
                counts = exporter.export_all(output, format_type, since)
                print(json.dumps({
                    "status": "success",
                    "type": "all",
                    "format": format_type,
                    "output": output,
                    "counts": counts,
                }, indent=2))
            elif export_type == "tasks":
                count = exporter.export_tasks(output, format_type, limit, since=since)
                print(json.dumps({
                    "status": "success",
                    "type": "tasks",
                    "count": count,
                    "output": output,
                }, indent=2))
            elif export_type == "memory":
                count = exporter.export_memory(output, format_type, limit)
                print(json.dumps({
                    "status": "success",
                    "type": "memory",
                    "count": count,
                    "output": output,
                }, indent=2))
            elif export_type == "audit":
                count = exporter.export_audit_log(output, format_type, since=since)
                print(json.dumps({
                    "status": "success",
                    "type": "audit",
                    "count": count,
                    "output": output,
                }, indent=2))
            elif export_type == "knowledge":
                count = exporter.export_knowledge_graph(output, format_type)
                print(json.dumps({
                    "status": "success",
                    "type": "knowledge",
                    "count": count,
                    "output": output,
                }, indent=2))
            else:
                print(json.dumps({"error": f"Unknown type: {export_type}"}))
                return False
        return True
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return False


def run_import(args):
    """Handle 'aios admin import' command."""
    from aios_core.data_export import DataImporter

    import_type = args.type
    format_type = args.format
    input_path = args.input
    db_path = getattr(args, "db", "aios.sqlite")

    try:
        with DataImporter(db_path) as importer:
            count = importer.import_tasks(input_path, format_type)
            print(json.dumps({
                "status": "success",
                "type": import_type,
                "count": count,
                "input": input_path,
            }, indent=2))
        return True
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return False


def run_keys_generate(args):
    """Handle 'aios admin keys generate' command."""
    from aios_core.secret_manager import SecretManager

    subject = args.subject
    roles = args.roles
    ttl = getattr(args, "ttl", None)
    prefix = getattr(args, "prefix", "aios")

    try:
        manager = SecretManager()
        key = manager.generate_key(subject, roles, ttl, prefix)
        print(json.dumps({
            "status": "success",
            "key": key.key,
            "subject": key.subject,
            "roles": key.roles,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
        }, indent=2))
        return True
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return False


def run_keys_list(args):
    """Handle 'aios admin keys list' command."""
    from aios_core.secret_manager import SecretManager

    manager = SecretManager()
    subject_filter = getattr(args, "subject", None)

    keys = manager.keys.values()
    if subject_filter:
        keys = [k for k in keys if k.subject == subject_filter]

    result = {
        "keys": [
            {
                "key_prefix": k.key[:16] + "...",
                "subject": k.subject,
                "roles": k.roles,
                "created_at": k.created_at,
                "expires_at": k.expires_at,
                "is_valid": k.is_valid(),
                "usage_count": k.usage_count,
            }
            for k in keys
        ],
        "total": len(list(keys)),
    }
    print(json.dumps(result, indent=2))
    return True


def run_keys_revoke(args):
    """Handle 'aios admin keys revoke' command."""
    from aios_core.secret_manager import SecretManager

    key = args.key
    reason = getattr(args, "reason", "")

    manager = SecretManager()
    success = manager.revoke_key(key, reason)

    if success:
        print(json.dumps({"status": "success", "message": "Key revoked"}))
    else:
        print(json.dumps({"error": "Key not found"}))
    return success


def run_keys_rotate(args):
    """Handle 'aios admin keys rotate' command."""
    from aios_core.secret_manager import SecretManager

    old_key = args.key
    ttl = getattr(args, "ttl", None)
    reason = getattr(args, "reason", "rotation")

    manager = SecretManager()
    new_key = manager.rotate_key(old_key, ttl, reason)

    if new_key:
        print(json.dumps({
            "status": "success",
            "new_key": new_key.key,
            "subject": new_key.subject,
            "roles": new_key.roles,
            "expires_at": new_key.expires_at,
        }, indent=2))
    else:
        print(json.dumps({"error": "Key not found"}))
    return new_key is not None


def run_keys_health(args):
    """Handle 'aios admin keys health' command."""
    from aios_core.secret_manager import SecretManager

    manager = SecretManager()
    report = manager.health_report()
    print(json.dumps(report, indent=2))
    return True


def run_backup_create(args):
    """Handle 'aios admin backup create' command."""
    from aios_core.backup_manager import BackupManager

    label = getattr(args, "label", "")
    mode = getattr(args, "mode", "full")
    db_path = getattr(args, "db", "aios.sqlite")
    backup_dir = getattr(args, "backup_dir", "./backups")

    try:
        manager = BackupManager(db_path=db_path, backup_dir=backup_dir)
        metadata = manager.create_backup(mode, label)
        print(json.dumps({
            "status": "success",
            "backup_id": metadata.backup_id,
            "size_bytes": metadata.size_bytes,
            "size_mb": round(metadata.size_bytes / 1024 / 1024, 2),
            "checksum": metadata.checksum[:16] + "...",
            "compressed": metadata.compressed,
            "created_at": metadata.created_at,
        }, indent=2))
        return True
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return False


def run_backup_list(args):
    """Handle 'aios admin backup list' command."""
    from aios_core.backup_manager import BackupManager

    db_path = getattr(args, "db", "aios.sqlite")
    backup_dir = getattr(args, "backup_dir", "./backups")

    manager = BackupManager(db_path=db_path, backup_dir=backup_dir)
    backups = manager.list_backups()

    result = {
        "backups": [
            {
                "backup_id": b.backup_id,
                "created_at": b.created_at,
                "size_mb": round(b.size_bytes / 1024 / 1024, 2),
                "checksum": b.checksum[:16] + "...",
                "compressed": b.compressed,
                "mode": b.mode,
            }
            for b in backups
        ],
        "total": len(backups),
    }
    print(json.dumps(result, indent=2))
    return True


def run_backup_verify(args):
    """Handle 'aios admin backup verify' command."""
    from aios_core.backup_manager import BackupManager

    backup_id = args.backup_id
    db_path = getattr(args, "db", "aios.sqlite")
    backup_dir = getattr(args, "backup_dir", "./backups")

    manager = BackupManager(db_path=db_path, backup_dir=backup_dir)
    is_valid = manager.verify_backup(backup_id)

    print(json.dumps({
        "backup_id": backup_id,
        "valid": is_valid,
        "status": "healthy" if is_valid else "corrupted",
    }, indent=2))
    return True


def run_backup_restore(args):
    """Handle 'aios admin backup restore' command."""
    from aios_core.backup_manager import BackupManager

    backup_id = args.backup_id
    target = getattr(args, "target", None)
    db_path = getattr(args, "db", "aios.sqlite")
    backup_dir = getattr(args, "backup_dir", "./backups")

    manager = BackupManager(db_path=db_path, backup_dir=backup_dir)
    success = manager.restore_backup(backup_id, target)

    if success:
        print(json.dumps({
            "status": "success",
            "backup_id": backup_id,
            "target": target or db_path,
        }, indent=2))
    else:
        print(json.dumps({"error": "Restore failed"}))
    return success


def run_backup_cleanup(args):
    """Handle 'aios admin backup cleanup' command."""
    from aios_core.backup_manager import BackupManager

    db_path = getattr(args, "db", "aios.sqlite")
    backup_dir = getattr(args, "backup_dir", "./backups")

    manager = BackupManager(db_path=db_path, backup_dir=backup_dir)
    removed = manager.cleanup_old_backups()

    print(json.dumps({
        "status": "success",
        "removed": removed,
        "remaining": len(manager.backups),
    }, indent=2))
    return True


def run_backup_health(args):
    """Handle 'aios admin backup health' command."""
    from aios_core.backup_manager import BackupManager

    db_path = getattr(args, "db", "aios.sqlite")
    backup_dir = getattr(args, "backup_dir", "./backups")

    manager = BackupManager(db_path=db_path, backup_dir=backup_dir)
    report = manager.health_report()
    schedule = manager.schedule_info()

    print(json.dumps({
        "health": report,
        "schedule": schedule,
    }, indent=2))
    return True
