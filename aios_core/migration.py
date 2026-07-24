"""AIOS Database Migration System v10.12.0.

Database migration: schema versioning, forward/backward
migration, dependency ordering, dry-run mode, validation,
and migration tracking.

Classes:
    Migration       — single migration step
    MigrationManager — full migration engine
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["Migration", "MigrationManager"]


class Migration:
    """Single database migration (backward-compatible)."""

    def __init__(
        self, version: str, description: str, up_sql: str, down_sql: str = ""
    ) -> None:
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql


class MigrationManager:
    """Database schema migration manager (backward-compatible)."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.migrations: list[Migration] = []
        self._dry_run: bool = False

    def add_migration(self, migration: Migration) -> None:
        """Add migration (backward-compatible)."""
        self.migrations.append(migration)

    def create_migrations_table(self, conn: sqlite3.Connection) -> None:
        """Create migrations table (backward-compatible)."""
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )

    def get_applied_versions(self, conn: sqlite3.Connection) -> set[str]:
        """Get applied versions (backward-compatible)."""
        try:
            rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
            return {row[0] for row in rows}
        except Exception:
            logger.warning("Failed to read schema_migrations")
            return set()

    def migrate(self) -> None:
        """Run forward migrations (backward-compatible)."""
        conn = sqlite3.connect(self.db_path)
        self.create_migrations_table(conn)
        applied = self.get_applied_versions(conn)

        for migration in sorted(self.migrations, key=lambda m: m.version):
            if migration.version not in applied:
                if self._dry_run:
                    logger.info("DRY RUN: Would apply migration %s", migration.version)
                else:
                    logger.info(
                        "Applying migration %s: %s",
                        migration.version,
                        migration.description,
                    )
                    conn.executescript(migration.up_sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES (?)",
                        (migration.version,),
                    )
                    conn.commit()

        conn.close()

    def rollback(self, target_version: str | None = None) -> dict[str, Any]:
        """Rollback migrations to target version."""
        if not self.migrations:
            return {"rolled_back": 0, "error": "no migrations"}

        conn = sqlite3.connect(self.db_path)
        self.create_migrations_table(conn)
        applied = self.get_applied_versions(conn)

        rolled_back_count = 0
        for migration in sorted(self.migrations, key=lambda m: m.version, reverse=True):
            if migration.version in applied:
                if target_version and migration.version <= target_version:
                    break
                if migration.down_sql:
                    conn.executescript(migration.down_sql)
                    conn.execute(
                        "DELETE FROM schema_migrations WHERE version = ?",
                        (migration.version,),
                    )
                    conn.commit()
                    rolled_back_count += 1

        conn.close()
        return {"rolled_back": rolled_back_count, "target": target_version}

    def dry_run(self, enable: bool = True) -> None:
        """Enable/disable dry run mode."""
        self._dry_run = enable

    def validate(self) -> dict[str, Any]:
        """Validate all migration SQL."""
        errors: list[str] = []
        for m in self.migrations:
            if not m.up_sql.strip():
                errors.append(f"Migration {m.version}: empty up_sql")
            if m.down_sql and not m.down_sql.strip():
                errors.append(f"Migration {m.version}: empty down_sql")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "migrations": len(self.migrations),
        }

    def status(self) -> dict[str, Any]:
        """Show migration status."""
        conn = sqlite3.connect(self.db_path)
        self.create_migrations_table(conn)
        applied = self.get_applied_versions(conn)
        conn.close()
        pending = [m.version for m in self.migrations if m.version not in applied]
        return {
            "applied": len(applied),
            "pending": len(pending),
            "total": len(self.migrations),
            "pending_versions": pending,
        }
