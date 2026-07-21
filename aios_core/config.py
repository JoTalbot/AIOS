"""AIOS Configuration v1.0.0

Centralised configuration from YAML files and environment variables.
Environment variables override YAML values.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


_DEFAULT_CONFIG = {
    "database": {
        "path": "aios.db",
    },
    "audit": {
        "file_path": "audit_log.jsonl",
        "retention_days": 90,
    },
    "approval": {
        "timeout_seconds": 86400,  # 24 hours
        "max_pending": 100,
    },
    "constitution": {
        "dir": "docs/constitution",
    },
    "policies": {
        "dir": "policies",
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    },
}


@dataclass
class DatabaseConfig:
    path: str = "aios.db"


@dataclass
class AuditConfig:
    file_path: str = "audit_log.jsonl"
    retention_days: int = 90


@dataclass
class ApprovalConfig:
    timeout_seconds: int = 86400
    max_pending: int = 100


@dataclass
class ConstitutionConfig:
    dir: str = "docs/constitution"


@dataclass
class PoliciesConfig:
    dir: str = "policies"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"


@dataclass
class AIOSConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)
    constitution: ConstitutionConfig = field(default_factory=ConstitutionConfig)
    policies: PoliciesConfig = field(default_factory=PoliciesConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    project_root: str = ""

    @classmethod
    def from_dict(cls, data: dict, project_root: str = "") -> "AIOSConfig":
        """Build config from a nested dict, falling back to defaults."""
        db_data = data.get("database", {})
        audit_data = data.get("audit", {})
        approval_data = data.get("approval", {})
        const_data = data.get("constitution", {})
        pol_data = data.get("policies", {})
        log_data = data.get("logging", {})

        return cls(
            database=DatabaseConfig(
                path=db_data.get("path", DatabaseConfig.path),
            ),
            audit=AuditConfig(
                file_path=audit_data.get("file_path", AuditConfig.file_path),
                retention_days=int(audit_data.get("retention_days", AuditConfig.retention_days)),
            ),
            approval=ApprovalConfig(
                timeout_seconds=int(approval_data.get("timeout_seconds", ApprovalConfig.timeout_seconds)),
                max_pending=int(approval_data.get("max_pending", ApprovalConfig.max_pending)),
            ),
            constitution=ConstitutionConfig(
                dir=const_data.get("dir", ConstitutionConfig.dir),
            ),
            policies=PoliciesConfig(
                dir=pol_data.get("dir", PoliciesConfig.dir),
            ),
            logging=LoggingConfig(
                level=log_data.get("level", LoggingConfig.level).upper(),
                format=log_data.get("format", LoggingConfig.format),
            ),
            project_root=project_root,
        )

    def resolve_path(self, relative_path: str) -> str:
        """Resolve a path relative to project_root if it's not absolute."""
        if os.path.isabs(relative_path):
            return relative_path
        if self.project_root:
            return os.path.join(self.project_root, relative_path)
        return relative_path


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge override into base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(config: dict) -> dict:
    """Apply AIOS_* environment variable overrides."""
    env_map = {
        "AIOS_DB_PATH": ("database", "path"),
        "AIOS_AUDIT_FILE": ("audit", "file_path"),
        "AIOS_AUDIT_RETENTION_DAYS": ("audit", "retention_days"),
        "AIOS_APPROVAL_TIMEOUT": ("approval", "timeout_seconds"),
        "AIOS_CONSTITUTION_DIR": ("constitution", "dir"),
        "AIOS_POLICIES_DIR": ("policies", "dir"),
        "AIOS_LOG_LEVEL": ("logging", "level"),
    }

    for env_var, (section, key) in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            # Numeric conversion for specific keys
            if key in ("retention_days", "timeout_seconds"):
                try:
                    value = int(value)
                except ValueError:
                    continue
            config.setdefault(section, {})[key] = value

    return config


def load_config(config_path: Optional[str] = None) -> AIOSConfig:
    """Load AIOS configuration.

    Priority (highest wins):
    1. AIOS_* environment variables
    2. YAML config file
    3. Built-in defaults

    Args:
        config_path: Path to aios_config.yaml. If None, searches standard locations.

    Returns:
        Fully resolved AIOSConfig instance.
    """
    # Determine project root (2 levels up from this file)
    this_dir = Path(__file__).resolve().parent
    project_root = str(this_dir.parent)

    # Find config file
    yaml_data = {}
    if config_path is None:
        candidates = [
            os.path.join(project_root, "aios_config.yaml"),
            os.path.join(project_root, "config", "aios_config.yaml"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                config_path = candidate
                break

    if config_path and os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    # Merge: defaults <- yaml <- env
    merged = _deep_merge(_DEFAULT_CONFIG, yaml_data)
    merged = _apply_env_overrides(merged)

    return AIOSConfig.from_dict(merged, project_root=project_root)