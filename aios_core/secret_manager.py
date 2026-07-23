"""Secret Rotation and Management for AIOS

Provides utilities for:
- API key generation and rotation
- Credential validation
- Secret expiration tracking
- Batch key rotation

Security best practices:
- Generate cryptographically secure keys
- Track key creation and expiration
- Support for key rollover without downtime
"""

import secrets
import hashlib
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class APIKey:
    """Represents an API key with metadata."""
    key: str
    subject: str
    roles: List[str]
    created_at: str
    expires_at: Optional[str] = None
    last_used: Optional[str] = None
    usage_count: int = 0
    revoked: bool = False

    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.revoked:
            return True
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.utcnow()

    def is_valid(self) -> bool:
        """Check if key is valid (not expired and not revoked)."""
        return not self.is_expired() and not self.revoked

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "APIKey":
        """Create from dictionary."""
        return cls(**data)


class SecretManager:
    """Manages API keys and secrets for AIOS."""

    def __init__(self, max_keys_per_subject: int = 5, default_ttl_days: int = 90):
        self.keys: Dict[str, APIKey] = {}
        self.max_keys_per_subject = max_keys_per_subject
        self.default_ttl_days = default_ttl_days
        self.rotation_log: List[Dict] = []

    def generate_key(
        self,
        subject: str,
        roles: List[str],
        ttl_days: Optional[int] = None,
        prefix: str = "aios",
    ) -> APIKey:
        """Generate a new API key.

        Args:
            subject: Key owner/subject
            roles: List of roles (admin, viewer, writer, operator, approver)
            ttl_days: Time-to-live in days (None = no expiration)
            prefix: Key prefix for identification

        Returns:
            New APIKey instance
        """
        # Enforce max keys per subject
        subject_keys = [k for k in self.keys.values() if k.subject == subject and not k.revoked]
        if len(subject_keys) >= self.max_keys_per_subject:
            raise ValueError(
                f"Subject '{subject}' has reached max keys ({self.max_keys_per_subject}). "
                "Revoke an existing key first."
            )

        # Generate cryptographically secure key
        raw_key = secrets.token_urlsafe(48)
        key = f"{prefix}_{raw_key}"

        now = datetime.utcnow()
        expires_at = None
        if ttl_days is not None:
            expires_at = (now + timedelta(days=ttl_days)).isoformat()

        api_key = APIKey(
            key=key,
            subject=subject,
            roles=roles,
            created_at=now.isoformat(),
            expires_at=expires_at,
            usage_count=0,
            revoked=False,
        )

        self.keys[key] = api_key

        # Log rotation
        self.rotation_log.append({
            "action": "created",
            "key_prefix": key[:12] + "...",
            "subject": subject,
            "roles": roles,
            "timestamp": now.isoformat(),
        })

        return api_key

    def revoke_key(self, key: str, reason: str = "") -> bool:
        """Revoke an API key.

        Args:
            key: The API key to revoke
            reason: Reason for revocation

        Returns:
            True if key was revoked, False if not found
        """
        if key not in self.keys:
            return False

        self.keys[key].revoked = True

        self.rotation_log.append({
            "action": "revoked",
            "key_prefix": key[:12] + "...",
            "subject": self.keys[key].subject,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return True

    def rotate_key(
        self, old_key: str, ttl_days: Optional[int] = None, reason: str = "rotation"
    ) -> Optional[APIKey]:
        """Rotate an API key (revoke old, create new with same subject/roles).

        Args:
            old_key: The old API key to replace
            ttl_days: TTL for new key (None = use default)
            reason: Reason for rotation

        Returns:
            New APIKey if rotation succeeded, None if old key not found
        """
        if old_key not in self.keys:
            return None

        old = self.keys[old_key]

        # Create new key with same subject/roles
        new_key = self.generate_key(
            subject=old.subject,
            roles=old.roles,
            ttl_days=ttl_days or self.default_ttl_days,
        )

        # Revoke old key
        self.revoke_key(old_key, reason=reason)

        self.rotation_log.append({
            "action": "rotated",
            "old_key_prefix": old_key[:12] + "...",
            "new_key_prefix": new_key.key[:12] + "...",
            "subject": old.subject,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return new_key

    def validate_key(self, key: str) -> Tuple[bool, Optional[APIKey]]:
        """Validate an API key.

        Args:
            key: The API key to validate

        Returns:
            Tuple of (is_valid, APIKey or None)
        """
        if key not in self.keys:
            return False, None

        api_key = self.keys[key]

        if not api_key.is_valid():
            return False, api_key

        # Update usage
        api_key.last_used = datetime.utcnow().isoformat()
        api_key.usage_count += 1

        return True, api_key

    def get_keys_by_subject(self, subject: str) -> List[APIKey]:
        """Get all keys for a subject."""
        return [k for k in self.keys.values() if k.subject == subject]

    def get_expired_keys(self) -> List[APIKey]:
        """Get all expired keys."""
        return [k for k in self.keys.values() if k.is_expired()]

    def get_expiring_keys(self, within_days: int = 7) -> List[APIKey]:
        """Get keys expiring within specified days."""
        threshold = datetime.utcnow() + timedelta(days=within_days)
        return [
            k for k in self.keys.values()
            if k.expires_at and not k.revoked
            and datetime.fromisoformat(k.expires_at) <= threshold
        ]

    def cleanup_revoked(self, older_than_days: int = 30) -> int:
        """Remove revoked keys older than specified days.

        Args:
            older_than_days: Remove keys revoked more than N days ago

        Returns:
            Number of keys removed
        """
        threshold = datetime.utcnow() - timedelta(days=older_than_days)
        to_remove = []

        for key, api_key in self.keys.items():
            if api_key.revoked:
                # Check if revoked long enough ago
                for log in reversed(self.rotation_log):
                    if log["action"] == "revoked" and log["key_prefix"] == key[:12] + "...":
                        revoked_at = datetime.fromisoformat(log["timestamp"])
                        if revoked_at < threshold:
                            to_remove.append(key)
                        break

        for key in to_remove:
            del self.keys[key]

        return len(to_remove)

    def export_keys(self, path: str) -> int:
        """Export keys to JSON file (for backup/migration).

        Args:
            path: Output file path

        Returns:
            Number of keys exported
        """
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "keys": [k.to_dict() for k in self.keys.values()],
            "rotation_log": self.rotation_log,
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return len(self.keys)

    def import_keys(self, path: str) -> int:
        """Import keys from JSON file.

        Args:
            path: Input file path

        Returns:
            Number of keys imported
        """
        with open(path, "r") as f:
            data = json.load(f)

        count = 0
        for key_data in data.get("keys", []):
            api_key = APIKey.from_dict(key_data)
            self.keys[api_key.key] = api_key
            count += 1

        self.rotation_log.extend(data.get("rotation_log", []))
        return count

    def health_report(self) -> Dict:
        """Generate health report for key management."""
        total = len(self.keys)
        active = len([k for k in self.keys.values() if k.is_valid()])
        expired = len(self.get_expired_keys())
        expiring = len(self.get_expiring_keys())
        revoked = len([k for k in self.keys.values() if k.revoked])

        return {
            "total_keys": total,
            "active_keys": active,
            "expired_keys": expired,
            "expiring_soon": expiring,
            "revoked_keys": revoked,
            "subjects": len(set(k.subject for k in self.keys.values())),
            "rotations_last_30d": len([
                l for l in self.rotation_log
                if l["action"] == "rotated"
                and datetime.fromisoformat(l["timestamp"]) > datetime.utcnow() - timedelta(days=30)
            ]),
        }

    def generate_env_export(self, path: str) -> None:
        """Generate AIOS_API_KEYS environment variable export.

        Args:
            path: Output file path (.env or .sh)
        """
        active_keys = {
            k.key: {"subject": k.subject, "roles": k.roles}
            for k in self.keys.values()
            if k.is_valid()
        }

        env_value = json.dumps(active_keys)

        with open(path, "w") as f:
            f.write(f'export AIOS_API_KEYS=\'{env_value}\'\n')


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AIOS Secret Manager")
    subparsers = parser.add_subparsers(dest="command")

    # Generate key
    gen = subparsers.add_parser("generate", help="Generate new API key")
    gen.add_argument("--subject", required=True, help="Key owner")
    gen.add_argument("--roles", nargs="+", default=["viewer"], help="Roles")
    gen.add_argument("--ttl", type=int, help="TTL in days")

    # Revoke key
    rev = subparsers.add_parser("revoke", help="Revoke API key")
    rev.add_argument("--key", required=True, help="Key to revoke")
    rev.add_argument("--reason", default="", help="Reason")

    # Rotate key
    rot = subparsers.add_parser("rotate", help="Rotate API key")
    rot.add_argument("--key", required=True, help="Old key")
    rot.add_argument("--ttl", type=int, help="New TTL in days")

    # List keys
    subparsers.add_parser("list", help="List all keys")

    # Health report
    subparsers.add_parser("health", help="Health report")

    # Export
    exp = subparsers.add_parser("export", help="Export keys")
    exp.add_argument("--path", default="keys_backup.json", help="Output path")

    args = parser.parse_args()

    manager = SecretManager()

    if args.command == "generate":
        key = manager.generate_key(args.subject, args.roles, args.ttl)
        print(f"Generated key: {key.key}")
        print(f"Subject: {key.subject}")
        print(f"Roles: {key.roles}")
        print(f"Expires: {key.expires_at or 'never'}")

    elif args.command == "list":
        for key in manager.keys.values():
            status = "✅" if key.is_valid() else "❌"
            print(f"{status} {key.key[:16]}... | {key.subject} | {key.roles}")

    elif args.command == "health":
        report = manager.health_report()
        for k, v in report.items():
            print(f"{k}: {v}")

    elif args.command == "export":
        count = manager.export_keys(args.path)
        print(f"Exported {count} keys to {args.path}")
