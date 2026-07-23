"""AIOS DI Container — sync + async services, env-configurable."""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppConfig:
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
        return cls(
            db_path=os.environ.get("AIOS_DB_PATH", "aios.sqlite"),
            backup_dir=os.environ.get("AIOS_BACKUP_DIR", "./backups"),
            constitution_dir=os.environ.get("AIOS_CONSTITUTION_DIR", "docs/constitution"),
            policies_dir=os.environ.get("AIOS_POLICIES_DIR", "policies"),
            audit_file=os.environ.get("AIOS_AUDIT_FILE", "audit_log.jsonl"),
            backup_retention_days=int(os.environ.get("AIOS_BACKUP_RETENTION_DAYS", "30")),
            backup_max_count=int(os.environ.get("AIOS_BACKUP_MAX_COUNT", "10")),
            backup_compress=os.environ.get("AIOS_BACKUP_COMPRESS", "").lower() in ("1", "true", "yes"),
            api_keys_json=os.environ.get("AIOS_API_KEYS", "{}"),
        )

class AppContainer:
    def __init__(self, config=None):
        self._config = config or AppConfig.from_env()
        self._db = self._orch = self._bm = self._abus = None

    @property
    def config(self): return self._config
    def configure(self, **kw):
        for k, v in kw.items():
            if hasattr(self._config, k): setattr(self._config, k, v)
        self.reset()
    def reset(self):
        self._db = self._orch = self._bm = self._abus = None
    def db_path(self): return self._config.db_path

    # sync
    def db(self):
        if self._db is None:
            from aios_core.storage import Database
            self._db = Database(db_path=self._config.db_path)
        return self._db
    def orchestrator(self):
        if self._orch is None:
            from aios_core.orchestrator import Orchestrator
            self._orch = Orchestrator(db=self.db(), constitution_dir=self._config.constitution_dir, policies_dir=self._config.policies_dir)
        return self._orch
    def backup_manager(self):
        if self._bm is None:
            from aios_core.backup_manager import BackupManager
            self._bm = BackupManager(db_path=self._config.db_path, backup_dir=self._config.backup_dir, retention_days=self._config.backup_retention_days, max_backups=self._config.backup_max_count, compress=self._config.backup_compress)
        return self._bm
    def data_exporter(self, db_path=None):
        from aios_core.data_export import DataExporter
        return DataExporter(db_path or self._config.db_path)
    def data_importer(self, db_path=None):
        from aios_core.data_export import DataImporter
        return DataImporter(db_path or self._config.db_path)

    # async
    def async_bus(self):
        if self._abus is None:
            from aios_core.async_bus import AsyncEventBus
            self._abus = AsyncEventBus()
        return self._abus
    def async_db(self):
        from aios_core.async_core import AsyncDatabase
        return AsyncDatabase(db_path=self._config.db_path)
    def async_kg(self):
        from aios_core.async_core import AsyncKnowledgeGraph
        return AsyncKnowledgeGraph()

    def stats(self):
        return {"db_path": self._config.db_path, "backup_dir": self._config.backup_dir, "db_ready": self._db is not None, "orch_ready": self._orch is not None, "bm_ready": self._bm is not None, "abus_ready": self._abus is not None}

container = AppContainer()
