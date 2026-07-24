"""Credential manager — secure storage and rotation for platform credentials.

Provides:
- Credential storage (encrypted at rest with app-level key derivation)
- Platform-specific credential schemas (OLX, Rozetka, TikTok, Facebook, etc.)
- Credential rotation with audit logging
- Expiry tracking and auto-rotation reminders
- Master key derivation from passphrase (PBKDF2-like)
- Credential masking for display (show only last 4 chars)

No external crypto libraries — uses stdlib hashlib + hmac for key derivation
and XOR-based stream cipher for encryption (suitable for app-level protection,
not suitable for production-grade security without adding real AES).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CredentialType(Enum):
    """Types of credentials stored."""

    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    COOKIE = "cookie"
    SSH_KEY = "ssh_key"
    PAT = "pat"  # Personal Access Token
    OAUTH = "oauth"
    TWO_FA_SECRET = "2fa_secret"


class RotationPolicy(Enum):
    """Credential rotation policies."""

    NEVER = "never"  # No automatic rotation
    DAILY = "daily"  # Rotate every 24 hours
    WEEKLY = "weekly"  # Rotate every 7 days
    MONTHLY = "monthly"  # Rotate every 30 days
    ON_EXPIRY = "on_expiry"  # Rotate when credential expires
    ON_COMPROMISE = "on_compromise"  # Rotate immediately on suspected compromise


@dataclass
class CredentialEntry:
    """A stored credential entry."""

    credential_id: str
    platform: str  # "olx", "rozetka", "tiktok", etc.
    credential_type: CredentialType
    username: str = ""  # Associated username/email
    value_encrypted: bytes = b""  # Encrypted credential value
    value_hash: str = ""  # SHA-256 hash for integrity check
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    last_rotated_at: float | None = None
    rotation_policy: RotationPolicy = RotationPolicy.MONTHLY
    rotation_count: int = 0
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_days(self) -> float:
        """Age of credential in days."""
        return (time.time() - self.created_at) / 86400

    @property
    def days_until_expiry(self) -> float | None:
        """Days until credential expires."""
        if self.expires_at is None:
            return None
        return (self.expires_at - time.time()) / 86400

    @property
    def needs_rotation(self) -> bool:
        """True if credential needs rotation based on policy."""
        if not self.is_active:
            return False

        if self.rotation_policy == RotationPolicy.NEVER:
            return False

        now = time.time()
        last = self.last_rotated_at or self.created_at

        if self.rotation_policy == RotationPolicy.DAILY:
            return now - last > 86400
        elif self.rotation_policy == RotationPolicy.WEEKLY:
            return now - last > 7 * 86400
        elif self.rotation_policy == RotationPolicy.MONTHLY:
            return now - last > 30 * 86400
        elif self.rotation_policy == RotationPolicy.ON_EXPIRY:
            if self.expires_at:
                return now > self.expires_at
            return False
        elif self.rotation_policy == RotationPolicy.ON_COMPROMISE:
            return False  # Only triggered manually

        return False


@dataclass
class RotationLog:
    """Log entry for a credential rotation."""

    credential_id: str
    old_hash: str
    new_hash: str
    rotated_at: float = field(default_factory=time.time)
    reason: str = "scheduled"
    rotated_by: str = "system"


@dataclass
class CredentialDisplay:
    """Masked credential for safe display."""

    credential_id: str
    platform: str
    credential_type: str
    username: str
    masked_value: str  # e.g. "****abcd"
    is_active: bool
    age_days: float
    needs_rotation: bool
    days_until_expiry: float | None


def _derive_key(passphrase: str, salt: bytes, iterations: int = 100000) -> bytes:
    """Derive encryption key from passphrase using PBKDF2-like construction.

    Uses HMAC-SHA256 for key derivation.

    Args:
        passphrase: Master passphrase.
        salt: Random salt bytes.
        iterations: Number of HMAC iterations.

    Returns:
        32-byte derived key.
    """
    key = passphrase.encode("utf-8")
    for _ in range(iterations):
        key = hmac.new(salt, key, hashlib.sha256).digest()
    return key


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    """XOR-based stream cipher encryption.

    Key is expanded to match data length via repeated hashing.

    Args:
        data: Plaintext bytes.
        key: 32-byte encryption key.

    Returns:
        Encrypted bytes.
    """
    if not data:
        return b""

    result = bytearray()
    chunk_key = key
    offset = 0

    while offset < len(data):
        # Generate chunk key by hashing previous
        chunk_key = hashlib.sha256(chunk_key + bytes([offset])).digest()

        # XOR chunk
        chunk_size = min(32, len(data) - offset)
        for i in range(chunk_size):
            result.append(data[offset + i] ^ chunk_key[i])
        offset += chunk_size

    return bytes(result)


def _xor_decrypt(data: bytes, key: bytes) -> bytes:
    """XOR-based stream cipher decryption (same as encryption).

    Args:
        data: Encrypted bytes.
        key: 32-byte encryption key.

    Returns:
        Decrypted bytes.
    """
    return _xor_encrypt(data, key)  # XOR is symmetric


def _mask_value(value: str, show_last: int = 4) -> str:
    """Mask credential value for display.

    Args:
        value: Original value.
        show_last: Number of chars to show at end.

    Returns:
        Masked string (e.g. "****abcd").
    """
    if len(value) <= show_last:
        return "****"
    return "*" * (len(value) - show_last) + value[-show_last:]


class CredentialManager:
    """Credential manager for secure storage and rotation.

    Provides:
    - store() — encrypt and store a credential
    - retrieve() — decrypt and retrieve a credential
    - rotate() — rotate credential with audit logging
    - list_credentials() — list all credentials (masked display)
    - check_rotations() — find credentials needing rotation
    - compromise() — immediate rotation on suspected compromise
    - export_audit_log() — export rotation history
    """

    def __init__(
        self,
        passphrase: str = "default-aios-key",
        salt: bytes | None = None,
        rotation_iterations: int = 100000,
    ) -> None:
        """Initialize CredentialManager.

        Args:
            passphrase: Master passphrase for key derivation.
            salt: Salt for key derivation (auto-generated if None).
            rotation_iterations: PBKDF2 iterations for key derivation.
        """
        self._salt = salt or os.urandom(16)
        self._key = _derive_key(passphrase, self._salt, rotation_iterations)
        self._credentials: dict[str, CredentialEntry] = {}
        self._rotation_log: list[RotationLog] = []
        self._counter: int = 0

    def _next_id(self) -> str:
        """Generate unique credential ID."""
        self._counter += 1
        return f"cred_{self._counter}"

    def store(
        self,
        platform: str,
        credential_type: CredentialType,
        value: str,
        username: str = "",
        expires_at: float | None = None,
        rotation_policy: RotationPolicy = RotationPolicy.MONTHLY,
        metadata: dict[str, Any] | None = None,
    ) -> CredentialEntry:
        """Store a credential (encrypted).

        Args:
            platform: Target platform.
            credential_type: Type of credential.
            value: Raw credential value (will be encrypted).
            username: Associated username.
            expires_at: Expiry timestamp (None = no expiry).
            rotation_policy: Rotation policy.
            metadata: Optional metadata.

        Returns:
            CredentialEntry (value is encrypted, original not stored).
        """
        cred_id = self._next_id()

        # Encrypt value
        encrypted = _xor_encrypt(value.encode("utf-8"), self._key)
        # Hash for integrity check
        value_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()

        entry = CredentialEntry(
            credential_id=cred_id,
            platform=platform,
            credential_type=credential_type,
            username=username,
            value_encrypted=encrypted,
            value_hash=value_hash,
            expires_at=expires_at,
            rotation_policy=rotation_policy,
            metadata=metadata or {},
        )

        self._credentials[cred_id] = entry
        return entry

    def retrieve(self, credential_id: str) -> str | None:
        """Decrypt and retrieve a credential value.

        Args:
            credential_id: Credential ID to retrieve.

        Returns:
            Decrypted value, or None if not found/integrity check failed.
        """
        entry = self._credentials.get(credential_id)
        if not entry or not entry.is_active:
            return None

        # Decrypt
        decrypted_bytes = _xor_decrypt(entry.value_encrypted, self._key)
        value = decrypted_bytes.decode("utf-8", errors="replace")

        # Integrity check
        current_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
        if current_hash != entry.value_hash:
            return None  # Integrity compromised

        return value

    def rotate(
        self,
        credential_id: str,
        new_value: str,
        reason: str = "scheduled",
        rotated_by: str = "system",
    ) -> CredentialEntry | None:
        """Rotate a credential with new value.

        Args:
            credential_id: Credential to rotate.
            new_value: New credential value.
            reason: Rotation reason.
            rotated_by: Who initiated rotation.

        Returns:
            Updated CredentialEntry, or None if not found.
        """
        entry = self._credentials.get(credential_id)
        if not entry:
            return None

        old_hash = entry.value_hash

        # Encrypt new value
        encrypted = _xor_encrypt(new_value.encode("utf-8"), self._key)
        new_hash = hashlib.sha256(new_value.encode("utf-8")).hexdigest()

        # Update entry
        entry.value_encrypted = encrypted
        entry.value_hash = new_hash
        entry.last_rotated_at = time.time()
        entry.rotation_count += 1

        # Log rotation
        self._rotation_log.append(
            RotationLog(
                credential_id=credential_id,
                old_hash=old_hash,
                new_hash=new_hash,
                reason=reason,
                rotated_by=rotated_by,
            )
        )

        return entry

    def compromise(
        self,
        credential_id: str,
        new_value: str,
        rotated_by: str = "admin",
    ) -> CredentialEntry | None:
        """Immediate rotation on suspected compromise.

        Args:
            credential_id: Compromised credential.
            new_value: New secure value.
            rotated_by: Who initiated emergency rotation.

        Returns:
            Updated CredentialEntry, or None.
        """
        return self.rotate(
            credential_id, new_value, reason="compromise", rotated_by=rotated_by
        )

    def deactivate(self, credential_id: str) -> CredentialEntry | None:
        """Deactivate a credential.

        Args:
            credential_id: Credential to deactivate.

        Returns:
            Deactivated CredentialEntry, or None.
        """
        entry = self._credentials.get(credential_id)
        if entry:
            entry.is_active = False
            return entry
        return None

    def activate(self, credential_id: str) -> CredentialEntry | None:
        """Re-activate a credential.

        Args:
            credential_id: Credential to activate.

        Returns:
            Activated CredentialEntry, or None.
        """
        entry = self._credentials.get(credential_id)
        if entry:
            entry.is_active = True
            return entry
        return None

    def list_credentials(
        self,
        platform: str | None = None,
        credential_type: CredentialType | None = None,
        active_only: bool = True,
    ) -> list[CredentialDisplay]:
        """List credentials (masked, safe for display).

        Args:
            platform: Filter by platform.
            credential_type: Filter by type.
            active_only: Only show active credentials.

        Returns:
            List of CredentialDisplay (masked values).
        """
        results = []
        for entry in self._credentials.values():
            if active_only and not entry.is_active:
                continue
            if platform and entry.platform != platform:
                continue
            if credential_type and entry.credential_type != credential_type:
                continue

            # Mask value
            raw_value = self.retrieve(entry.credential_id)
            masked = _mask_value(raw_value or "")

            results.append(
                CredentialDisplay(
                    credential_id=entry.credential_id,
                    platform=entry.platform,
                    credential_type=entry.credential_type.value,
                    username=entry.username,
                    masked_value=masked,
                    is_active=entry.is_active,
                    age_days=round(entry.age_days, 1),
                    needs_rotation=entry.needs_rotation,
                    days_until_expiry=round(entry.days_until_expiry, 1)
                    if entry.days_until_expiry
                    else None,
                )
            )

        return results

    def check_rotations(self) -> list[CredentialEntry]:
        """Find all credentials that need rotation.

        Returns:
            List of CredentialEntry needing rotation.
        """
        return [e for e in self._credentials.values() if e.needs_rotation]

    def get_entry(self, credential_id: str) -> CredentialEntry | None:
        """Get credential entry (metadata only, no value).

        Args:
            credential_id: Credential ID.

        Returns:
            CredentialEntry or None.
        """
        return self._credentials.get(credential_id)

    def export_audit_log(self) -> list[dict[str, Any]]:
        """Export rotation audit log.

        Returns:
            List of rotation log dicts.
        """
        return [
            {
                "credential_id": log.credential_id,
                "old_hash": log.old_hash,
                "new_hash": log.new_hash,
                "rotated_at": log.rotated_at,
                "reason": log.reason,
                "rotated_by": log.rotated_by,
            }
            for log in self._rotation_log
        ]

    def stats(self) -> dict[str, Any]:
        """Credential manager statistics.

        Returns:
            Dict with total, active, needing_rotation, etc.
        """
        total = len(self._credentials)
        active = sum(1 for e in self._credentials.values() if e.is_active)
        needing_rotation = len(self.check_rotations())
        platform_counts: dict[str, int] = {}
        for e in self._credentials.values():
            platform_counts[e.platform] = platform_counts.get(e.platform, 0) + 1

        return {
            "total_credentials": total,
            "active_credentials": active,
            "inactive_credentials": total - active,
            "needing_rotation": needing_rotation,
            "rotation_count": len(self._rotation_log),
            "platforms": platform_counts,
        }

    def rekey(self, new_passphrase: str, iterations: int = 100000) -> int:
        """Re-encrypt all credentials with a new passphrase.

        Args:
            new_passphrase: New master passphrase.
            iterations: PBKDF2 iterations.

        Returns:
            Number of credentials re-encrypted.
        """
        new_salt = os.urandom(16)
        new_key = _derive_key(new_passphrase, new_salt, iterations)

        count = 0
        for entry in self._credentials.values():
            # Decrypt with old key
            old_value = self.retrieve(entry.credential_id)
            if old_value is None:
                continue

            # Re-encrypt with new key
            new_encrypted = _xor_encrypt(old_value.encode("utf-8"), new_key)
            entry.value_encrypted = new_encrypted
            count += 1

        # Update master key and salt
        self._key = new_key
        self._salt = new_salt

        return count
