"""Secrets Manager for AIOS"""

import os
from typing import Optional


class SecretsManager:
    """Simple secrets manager (env + in-memory)."""

    def __init__(self):
        self._secrets = {}

    def set(self, key: str, value: str):
        self._secrets[key] = value

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        # Priority: env > memory > default
        return os.getenv(key) or self._secrets.get(key, default)

    def delete(self, key: str):
        self._secrets.pop(key, None)

    def list_keys(self) -> list:
        return list(self._secrets.keys())


secrets = SecretsManager()