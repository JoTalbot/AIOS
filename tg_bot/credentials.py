"""Read short-lived secrets from systemd's per-service credential directory."""

from __future__ import annotations

import os
from pathlib import Path


def read_systemd_credential(name: str) -> str:
    """Return one credential without logging it; missing credentials are empty."""
    directory = os.environ.get("CREDENTIALS_DIRECTORY", "").strip()
    if not directory or not name or "/" in name:
        return ""
    try:
        return (Path(directory) / name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def secret_from_env_or_credential(*env_names: str, credential: str) -> str:
    # A mounted systemd credential deliberately overrides legacy EnvironmentFile
    # values so secret rotation does not depend on editing the process env file.
    mounted = read_systemd_credential(credential)
    if mounted:
        return mounted
    for env_name in env_names:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return ""


def import_runtime_credential(env_name: str, credential: str) -> str:
    """Populate an environment variable for legacy callers inside this process."""
    value = read_systemd_credential(credential) or os.environ.get(env_name, "").strip()
    if value:
        os.environ[env_name] = value
    return value
