"""Secrets Manager for AIOS v10.6.0.

Enhanced secrets management with encryption, rotation policies,
secret versions, access audit, namespace isolation, and masking.

Classes:
    SecretVersion   — versioned secret entry
    RotationPolicy  — automatic rotation schedule
    SecretsManager  — enhanced manager with encryption, rotation, audit
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Secret Version ───────────────────────────────────────────────────────────


@dataclass
class SecretVersion:
    """Versioned secret entry."""

    key: str
    value: str
    version: int = 1
    created_at: float = field(default_factory=time.time)
    rotated_at: float | None = None
    namespace: str = "default"


# ── Rotation Policy ─────────────────────────────────────────────────────────


@dataclass
class RotationPolicy:
    """Automatic rotation schedule for a secret."""

    key: str
    interval_days: int = 90
    last_rotated: float = 0.0
    auto_generate: bool = False  # auto-generate new value on rotation

    def is_due(self) -> bool:
        """Check if rotation is due."""
        if self.last_rotated == 0:
            return False
        days_since = (time.time() - self.last_rotated) / 86400
        return days_since >= self.interval_days


# ── Secrets Manager ─────────────────────────────────────────────────────────


class SecretsManager:
    """Enhanced secrets manager with encryption, rotation, and audit.

    Features:
    - Environment variable + in-memory secret storage
    - Namespace isolation (separate secret spaces)
    - Secret versioning (history of changes)
    - Rotation policies with auto-generation
    - Access audit trail
    - Value masking for safe display
    - Simple XOR encryption for in-memory secrets
    """

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}
        self._encrypted: dict[str, str] = {}
        self._versions: dict[str, list[SecretVersion]] = {}
        self._namespaces: dict[str, dict[str, str]] = {}  # ns → secrets
        self._rotation_policies: dict[str, RotationPolicy] = {}
        self._audit_log: list[dict[str, Any]] = []
        self._encryption_key: str = "aios_default_key_2024"

    # ── Set / Get ──────────────────────────────────────────────

    def set(
        self, key: str, value: str, namespace: str = "default", encrypt: bool = False
    ) -> None:
        """Set a secret value."""
        # Store in namespace
        if namespace not in self._namespaces:
            self._namespaces[namespace] = {}
        self._namespaces[namespace][key] = value

        # Store in main dict (default namespace)
        self._secrets[key] = value

        # Encrypt if requested
        if encrypt:
            self._encrypted[key] = self._xor_encrypt(value)

        # Track version
        if key not in self._versions:
            self._versions[key] = []
        version_num = len(self._versions[key]) + 1
        self._versions[key].append(
            SecretVersion(
                key=key,
                value=value,
                version=version_num,
                namespace=namespace,
            )
        )

        self._audit("set", {"key": key, "namespace": namespace, "encrypted": encrypt})

    def get(
        self, key: str, default: str | None = None, namespace: str = "default"
    ) -> str | None:
        """Get a secret value. Priority: env > namespace > main dict > default."""
        # Priority: environment variable
        env_val = os.getenv(key)
        if env_val:
            return env_val

        # Namespace lookup
        ns_secrets = self._namespaces.get(namespace, {})
        if key in ns_secrets:
            self._audit(
                "get", {"key": key, "namespace": namespace, "source": "namespace"}
            )
            return ns_secrets[key]

        # Main dict
        if key in self._secrets:
            self._audit("get", {"key": key, "source": "memory"})
            return self._secrets[key]

        self._audit("get", {"key": key, "source": "default"})
        return default

    def get_encrypted(self, key: str) -> str | None:
        """Get and decrypt an encrypted secret."""
        if key not in self._encrypted:
            return None
        return self._xor_decrypt(self._encrypted[key])

    # ── Delete ─────────────────────────────────────────────────

    def delete(self, key: str, namespace: str = "default") -> None:
        """Delete a secret."""
        self._secrets.pop(key, None)
        self._encrypted.pop(key, None)
        ns = self._namespaces.get(namespace, {})
        ns.pop(key, None)
        self._audit("delete", {"key": key, "namespace": namespace})

    # ── Versioning ─────────────────────────────────────────────

    def get_versions(self, key: str) -> list[SecretVersion]:
        """Return all versions of a secret."""
        return self._versions.get(key, [])

    def get_version(self, key: str, version: int) -> str | None:
        """Return specific version value."""
        versions = self._versions.get(key, [])
        for v in versions:
            if v.version == version:
                return v.value
        return None

    # ── Rotation ───────────────────────────────────────────────

    def set_rotation_policy(
        self, key: str, interval_days: int = 90, auto_generate: bool = False
    ) -> RotationPolicy:
        """Set rotation policy for a secret."""
        policy = RotationPolicy(
            key=key, interval_days=interval_days, auto_generate=auto_generate
        )
        self._rotation_policies[key] = policy
        return policy

    def rotate(self, key: str, new_value: str | None = None) -> str | None:
        """Rotate a secret (manual or auto-generated)."""
        policy = self._rotation_policies.get(key)
        if new_value is None and policy and policy.auto_generate:
            new_value = self._generate_secret()

        if new_value is None:
            return None

        self.set(key, new_value)
        if policy:
            policy.last_rotated = time.time()

        self._audit("rotate", {"key": key, "auto": new_value is not None})
        return new_value

    def check_rotations(self) -> list[str]:
        """Check which secrets need rotation."""
        due = []
        for key, policy in self._rotation_policies.items():
            if policy.is_due():
                due.append(key)
        return due

    # ── Masking ────────────────────────────────────────────────

    def mask(self, value: str, show_chars: int = 4) -> str:
        """Mask a secret value for safe display."""
        if len(value) <= show_chars:
            return "*" * len(value)
        return "*" * (len(value) - show_chars) + value[-show_chars:]

    # ── Namespace ──────────────────────────────────────────────

    def list_namespace(self, namespace: str = "default") -> list[str]:
        """List keys in a namespace."""
        return list(self._namespaces.get(namespace, {}).keys())

    def list_keys(self) -> list:
        """List all secret keys (backward-compatible)."""
        return list(self._secrets.keys())

    # ── Audit ──────────────────────────────────────────────────

    def get_audit_log(
        self, key: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return audit events, optionally filtered by key."""
        if key:
            return [e for e in self._audit_log if e.get("key") == key][-limit:]
        return self._audit_log[-limit:]

    # ── Encryption ─────────────────────────────────────────────

    def _xor_encrypt(self, value: str) -> str:
        """Simple XOR stream cipher encryption."""
        key_bytes = self._encryption_key.encode()
        value_bytes = value.encode()
        encrypted = bytearray()
        for i, b in enumerate(value_bytes):
            encrypted.append(b ^ key_bytes[i % len(key_bytes)])
        return encrypted.hex()

    def _xor_decrypt(self, hex_value: str) -> str:
        """Decrypt XOR-encrypted value."""
        key_bytes = self._encryption_key.encode()
        encrypted = bytes.fromhex(hex_value)
        decrypted = bytearray()
        for i, b in enumerate(encrypted):
            decrypted.append(b ^ key_bytes[i % len(key_bytes)])
        return decrypted.decode()

    def _generate_secret(self) -> str:
        """Generate a random secret value."""
        raw = os.urandom(32).hex()
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    # ── Audit helper ───────────────────────────────────────────

    def _audit(self, action: str, details: dict[str, Any]) -> None:
        self._audit_log.append({"action": action, "timestamp": time.time(), **details})


secrets = SecretsManager()
