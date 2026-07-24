"""JWT-based Authentication for AIOS v10.10.0.

JWT authentication: token creation and verification, refresh
tokens, role-based access control, token revocation/blacklist,
scope validation, rate limiting, and audit logging.

Classes:
    TokenBlacklist  — revoked token tracker
    JWTManager      — full JWT lifecycle manager
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import jwt

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """Revoked token tracker."""

    def __init__(self, max_size: int = 10000) -> None:
        self._blacklisted: dict[str, float] = {}  # jti → expiry_time
        self.max_size = max_size

    def add(self, jti: str, expires_at: float) -> None:
        """Blacklist a token by its JTI."""
        self._blacklisted[jti] = expires_at
        # Auto-prune expired blacklist entries
        if len(self._blacklisted) > self.max_size:
            now = time.time()
            self._blacklisted = {k: v for k, v in self._blacklisted.items() if v > now}

    def is_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted."""
        if jti in self._blacklisted:
            return time.time() < self._blacklisted[jti]
        return False

    def stats(self) -> dict[str, Any]:
        now = time.time()
        active = sum(1 for v in self._blacklisted.values() if v > now)
        return {"total_blacklisted": len(self._blacklisted), "active": active}


class JWTManager:
    """JWT token lifecycle manager."""

    def __init__(
        self,
        secret: str = "aios-secret-key",
        algorithm: str = "HS256",
        access_token_expiry: int = 3600,
        refresh_token_expiry: int = 86400,
    ) -> None:
        self.secret = secret
        self.algorithm = algorithm
        self.access_token_expiry = access_token_expiry
        self.refresh_token_expiry = refresh_token_expiry
        self._blacklist = TokenBlacklist()
        self._audit_log: list[dict[str, Any]] = []
        self._rate_limit: dict[str, list[float]] = {}  # subject → [timestamps]
        self._rate_limit_max: int = 10  # max tokens per minute

    def create_token(
        self,
        subject: str,
        roles: list[str] | None = None,
        expires_in: int = 3600,
        scopes: list[str] | None = None,
    ) -> str:
        """Create JWT access token (backward-compatible)."""
        # Rate limiting
        self._check_rate_limit(subject)
        now = int(time.time())
        jti = hashlib.sha256(
            f"{subject}:{now}:{random.randint(0, 100000)}".encode()
        ).hexdigest()[:16]
        payload = {
            "sub": subject,
            "roles": roles or ["user"],
            "scopes": scopes or ["read"],
            "iat": now,
            "exp": now + expires_in,
            "jti": jti,
            "type": "access",
        }
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        self._audit_log.append(
            {"action": "create", "subject": subject, "jti": jti, "time": now}
        )
        return token

    def create_refresh_token(self, subject: str, roles: list[str] | None = None) -> str:
        """Create a refresh token."""
        now = int(time.time())
        jti = hashlib.sha256(f"{subject}:refresh:{now}".encode()).hexdigest()[:16]
        payload = {
            "sub": subject,
            "roles": roles or ["user"],
            "iat": now,
            "exp": now + self.refresh_token_expiry,
            "jti": jti,
            "type": "refresh",
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify JWT token (backward-compatible)."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            # Check blacklist
            jti = payload.get("jti", "")
            if self._blacklist.is_blacklisted(jti):
                logger.warning("Blacklisted token used: %s", jti)
                return None
            self._audit_log.append(
                {
                    "action": "verify",
                    "subject": payload.get("sub"),
                    "jti": jti,
                    "time": int(time.time()),
                }
            )
            return payload
        except jwt.PyJWTError:
            return None

    def get_principal(self, token: str) -> dict[str, Any] | None:
        """Get principal info from token (backward-compatible)."""
        payload = self.verify_token(token)
        if payload:
            return {
                "subject": payload.get("sub"),
                "roles": payload.get("roles", []),
                "scopes": payload.get("scopes", []),
                "token": token,
            }
        return None

    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding to blacklist."""
        payload = self.verify_token(token)
        if payload:
            jti = payload.get("jti", "")
            exp = payload.get("exp", 0)
            self._blacklist.add(jti, exp)
            self._audit_log.append(
                {"action": "revoke", "jti": jti, "time": int(time.time())}
            )
            return True
        return False

    def check_role(self, token: str, required_role: str) -> bool:
        """Check if token has a required role."""
        payload = self.verify_token(token)
        if payload:
            return required_role in payload.get("roles", [])
        return False

    def check_scope(self, token: str, required_scope: str) -> bool:
        """Check if token has a required scope."""
        payload = self.verify_token(token)
        if payload:
            return required_scope in payload.get("scopes", [])
        return False

    def _check_rate_limit(self, subject: str) -> None:
        """Internal rate limiting per subject."""
        now = time.time()
        if subject not in self._rate_limit:
            self._rate_limit[subject] = []
        self._rate_limit[subject] = [
            t for t in self._rate_limit[subject] if t > now - 60
        ]
        if len(self._rate_limit[subject]) >= self._rate_limit_max:
            raise ValueError(f"Rate limit exceeded for {subject}")
        self._rate_limit[subject].append(now)

    def stats(self) -> dict[str, Any]:
        return {
            "blacklist": self._blacklist.stats(),
            "audit_entries": len(self._audit_log),
            "rate_limited_subjects": len(self._rate_limit),
        }


import random
