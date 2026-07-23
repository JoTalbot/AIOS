"""AIOS Dependency Injection Container.

Centralises creation of all major services — Database, Orchestrator,
BackupManager, DataExporter — so config flows from env vars rather
than hardcoded strings.

Usage::
    from aios_core.container import container

__all__ = ["AppConfig", "AppContainer", "container"]
    db = container.db()
    orch = container.orchestrator()

Override via env::
    AIOS_DB_PATH=/data/aios.sqlite
    AIOS_BACKUP_DIR=/data/backups
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    """Central configuration for all AIOS services."""

    db_path: str = "aios.sqlite"
    backup_dir: str = "./backups"
    constitution_dir: str = "docs/constitution"
    policies_dir: str = "policies"
    audit_file: str = "audit_log.jsonl"
    backup_retention_days: int = 30
    backup_max_count: int = 10
    backup_compress: bool = False
    api_keys_json: str = "{}"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build configuration from environment variables."""
        return cls(
            db_path=os.environ.get("AIOS_DB_PATH", "aios.sqlite"),
            backup_dir=os.environ.get("AIOS_BACKUP_DIR", "./backups"),
            constitution_dir=os.environ.get(
                "AIOS_CONSTITUTION_DIR", "docs/constitution"
            ),
            policies_dir=os.environ.get("AIOS_POLICIES_DIR", "policies"),
            audit_file=os.environ.get("AIOS_AUDIT_FILE", "audit_log.jsonl"),
            backup_retention_days=int(
                os.environ.get("AIOS_BACKUP_RETENTION_DAYS", "30")
            ),
            backup_max_count=int(
                os.environ.get("AIOS_BACKUP_MAX_COUNT", "10")
            ),
            backup_compress=os.environ.get(
                "AIOS_BACKUP_COMPRESS", ""
            ).lower() in ("1", "true", "yes"),
            api_keys_json=os.environ.get("AIOS_API_KEYS", "{}"),
        )


class AppContainer:
    """Lazy service container — singletons created on first access."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self._config = config or AppConfig.from_env()
        self._db: object | None = None
        self._orchestrator: object | None = None
        self._backup_manager: object | None = None

    @property
    def config(self) -> AppConfig:
        """Return the current configuration."""
        return self._config

    def configure(self, **kwargs) -> None:
        """Update config and reset cached services."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.reset()

    def reset(self) -> None:
        """Drop all cached service instances."""
        self._db = None
        self._orchestrator = None
        self._backup_manager = None

    def db_path(self) -> str:
        """Return configured database path."""
        return self._config.db_path

    def db(self):
        """Return shared Database singleton."""
        if self._db is None:
            from aios_core.storage import Database
            self._db = Database(db_path=self._config.db_path)
        return self._db

    def orchestrator(self):
        """Return shared Orchestrator singleton."""
        if self._orchestrator is None:
            from aios_core.orchestrator import Orchestrator
            self._orchestrator = Orchestrator(
                db=self.db(),
                constitution_dir=self._config.constitution_dir,
                policies_dir=self._config.policies_dir,
            )
        return self._orchestrator

    def backup_manager(self):
        """Return shared BackupManager singleton."""
        if self._backup_manager is None:
            from aios_core.backup_manager import BackupManager
            self._backup_manager = BackupManager(
                db_path=self._config.db_path,
                backup_dir=self._config.backup_dir,
                retention_days=self._config.backup_retention_days,
                max_backups=self._config.backup_max_count,
                compress=self._config.backup_compress,
            )
        return self._backup_manager

    def data_exporter(self, db_path: Optional[str] = None):
        """Return DataExporter bound to configured database."""
        from aios_core.data_export import DataExporter
        return DataExporter(db_path or self._config.db_path)

    def data_importer(self, db_path: Optional[str] = None):
        """Return DataImporter bound to configured database."""
        from aios_core.data_export import DataImporter
        return DataImporter(db_path or self._config.db_path)

    def stats(self) -> dict:
        """Return container metadata for debugging."""
        return {
            "db_path": self._config.db_path,
            "backup_dir": self._config.backup_dir,
            "constitution_dir": self._config.constitution_dir,
            "db_initialized": self._db is not None,
            "orchestrator_initialized": self._orchestrator is not None,
            "backup_manager_initialized": self._backup_manager is not None,
        }


# Global singleton
container = AppContainer()
