"""Centralised YAML Configuration System.

Loads ``aios_config.yaml`` (or path from ``AIOS_CONFIG`` env var)
and provides typed access to all settings.  Environment variables
override YAML values (``AIOS_DB_PATH`` beats ``database.path``).

Usage::

    from aios_core.config_central import load_config
    cfg = load_config()
    print(cfg.database.path)
"""


import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass
class DatabaseConfig:
    path: str = "aios.sqlite"


@dataclass
class BackupConfig:
    directory: str = "./backups"
    retention_days: int = 30
    max_backups: int = 10
    compress: bool = False


@dataclass
class AuditConfig:
    file_path: str = "audit_log.jsonl"
    retention_days: int = 90


@dataclass
class ConstitutionConfig:
    directory: str = "docs/constitution"


@dataclass
class PoliciesConfig:
    directory: str = "policies"


@dataclass
class APIKeysConfig:
    """API key definitions.  In YAML this is a dict of subject→config."""

    keys: Dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class PlatformConfig:
    """Per-platform configuration block."""

    name: str = ""
    package: str = ""
    enabled: bool = True
    profiles: Dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class PlatformsConfig:
    """All registered platform configurations."""

    platforms: Dict[str, dict] = field(default_factory=dict)


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"


@dataclass
class PacingConfig:
    actions_per_hour: int = 60
    jitter_seconds: float = 1.6


@dataclass
class WebhookConfig:
    url: str = ""
    chat_id: str = ""


@dataclass
class AIOSConfig:
    """Root configuration object — one section per subsystem."""

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    constitution: ConstitutionConfig = field(default_factory=ConstitutionConfig)
    policies: PoliciesConfig = field(default_factory=PoliciesConfig)
    api_keys: dict = field(default_factory=dict)
    platforms: PlatformsConfig = field(default_factory=PlatformsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    pacing: PacingConfig = field(default_factory=PacingConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

# Map of YAML top-level keys → dataclass field names and classes
_SECTION_MAP: Dict[str, tuple] = {
    "database": ("database", DatabaseConfig),
    "backup": ("backup", BackupConfig),
    "audit": ("audit", AuditConfig),
    "constitution": ("constitution", ConstitutionConfig),
    "policies": ("policies", PoliciesConfig),
    "api_keys": ("api_keys", APIKeysConfig),
    "platforms": ("platforms", PlatformsConfig),
    "logging": ("logging", LoggingConfig),
    "pacing": ("pacing", PacingConfig),
    "webhook": ("webhook", WebhookConfig),
}

# Map of env vars → dataclass.field_path for overrides
_ENV_OVERRIDES: Dict[str, tuple] = {
    "AIOS_DB_PATH": ("database", "path"),
    "AIOS_BACKUP_DIR": ("backup", "directory"),
    "AIOS_BACKUP_RETENTION_DAYS": ("backup", "retention_days"),
    "AIOS_BACKUP_MAX_COUNT": ("backup", "max_backups"),
    "AIOS_BACKUP_COMPRESS": ("backup", "compress"),
    "AIOS_CONSTITUTION_DIR": ("constitution", "directory"),
    "AIOS_POLICIES_DIR": ("policies", "directory"),
    "AIOS_LOG_LEVEL": ("logging", "level"),
    "AIOS_PACING_ACTIONS_PER_HOUR": ("pacing", "actions_per_hour"),
    "AIOS_API_KEYS": ("api_keys", "keys"),
}


def _apply_env_overrides(cfg: AIOSConfig) -> None:
    """Override dataclass fields from environment variables."""
    for env_var, (section_name, field_name) in _ENV_OVERRIDES.items():
        value = os.environ.get(env_var)
        if value is None:
            continue
        section = getattr(cfg, section_name)
        if field_name == "compress":
            setattr(section, field_name, value.lower() in ("1", "true", "yes"))
        elif field_name == "keys":
            import json

            setattr(section, field_name, json.loads(value))
        elif hasattr(section, field_name):
            ftype = type(getattr(section, field_name))
            setattr(section, field_name, ftype(value))


def load_config(path: str | None = None) -> AIOSConfig:
    """Load configuration from YAML file with env-var overrides.

    Resolution order:
    1. Defaults from dataclass field values
    2. ``aios_config.yaml`` in project root (or *path*)
    3. Environment variables (beat everything)

    Returns ``AIOSConfig`` with all sections resolved.
    """
    cfg = AIOSConfig()

    # Try YAML
    config_path = Path(path or os.environ.get("AIOS_CONFIG", "aios_config.yaml"))
    if config_path.exists():
        with open(config_path) as fh:
            data = yaml.safe_load(fh) or {}

        for yaml_key, (dc_field, dc_class) in _SECTION_MAP.items():
            if yaml_key in data:
                section_data = data[yaml_key]
                if isinstance(section_data, dict):
                    # Build dataclass from dict — only pass known fields
                    known = {f.name for f in fields(dc_class)}
                    filtered = {k: v for k, v in section_data.items() if k in known}
                    setattr(cfg, dc_field, dc_class(**filtered))

    # Env overrides
    _apply_env_overrides(cfg)
    return cfg


def generate_default_config(path: str = "aios_config.yaml") -> str:
    """Write a default ``aios_config.yaml`` to *path* and return the YAML text."""
    yaml_text = """# AIOS Configuration — generated on {ts}
# Environment variables (AIOS_DB_PATH, etc.) override these values.

database:
  path: aios.sqlite

backup:
  directory: ./backups
  retention_days: 30
  max_backups: 10
  compress: false

audit:
  file_path: audit_log.jsonl
  retention_days: 90

constitution:
  directory: docs/constitution

policies:
  directory: policies

logging:
  level: INFO
  format: "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

pacing:
  actions_per_hour: 60
  jitter_seconds: 1.6

webhook:
  url: ""
  chat_id: ""

platforms:
  olx:
    name: olx
    package: ua.slando
    enabled: true
  instagram:
    name: instagram
    package: com.instagram.android
    enabled: true
  facebook:
    name: facebook
    package: com.facebook.katana
    enabled: true
""".format(ts=__import__("datetime").datetime.now().isoformat())

    Path(path).write_text(yaml_text)
    return yaml_text
