"""Compatibility bridge: aios_core.secrets -> aios_core.aios_secrets.

Some tests/history reference `from aios_core.secrets import SecretsManager`.
Re-export from the real module for backward compatibility.
"""
from __future__ import annotations

from .aios_secrets import SecretsManager, SecretVersion, RotationPolicy

# A convenience instance named 'secrets' (as some callers expect).
secrets = SecretsManager()

__all__ = ["SecretsManager", "SecretVersion", "RotationPolicy", "secrets"]
