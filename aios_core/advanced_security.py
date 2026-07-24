"""Advanced Security Module for AIOS v10.7.0.

Multi-layer security: threat detection with signature patterns,
rate-based brute-force detection, input sanitization, HMAC integrity,
API key management with rotation, and security audit trail.

Classes:
    ThreatLevel    — severity of detected threats
    ThreatEvent    — recorded threat with details
    SecurityPolicy — configurable detection rule
    AdvancedSecurity — full security engine with detection, sanitization, audit
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat severity."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ThreatEvent:
    """Recorded threat event."""

    threat_type: str
    level: ThreatLevel
    details: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False


@dataclass
class SecurityPolicy:
    """Configurable detection rule."""

    name: str
    threat_type: str
    level: ThreatLevel = ThreatLevel.MEDIUM
    check_fn: Callable[[dict[str, Any]], bool] | None = None
    action: str = "log"  # log, block, alert


class AdvancedSecurity:
    """Full security engine with detection, sanitization, integrity, audit.

    Features:
    - Threat detection with custom policies
    - Brute-force detection (rate-based)
    - Input sanitization (XSS, injection patterns)
    - HMAC integrity verification
    - API key management with rotation
    - Security audit trail
    """

    def __init__(self) -> None:
        self.threats: list[ThreatEvent] = []
        self.policies: dict[str, SecurityPolicy] = {}
        self.api_keys: dict[
            str, dict[str, Any]
        ] = {}  # key → {name, created, expires, active}
        self._rate_counters: dict[str, list[float]] = {}  # ip → timestamps
        self._brute_force_threshold: int = 10  # requests per 60s
        self._xss_patterns: list[str] = [r"<script", r"javascript:", r"on\w+="]
        self._injection_patterns: list[str] = [
            r";\s*DROP",
            r"'\s*OR\s+'",
            r"UNION\s+SELECT",
        ]

    # ── Threat Detection ────────────────────────────────────────

    def add_policy(self, policy: SecurityPolicy) -> None:
        """Add a detection policy."""
        self.policies[policy.name] = policy

    def detect_threat(self, request: dict[str, Any]) -> bool:
        """Detect threats using policies and built-in checks."""
        detected = False

        # Built-in: suspicious IP
        ip = request.get("ip", "")
        if ip in ("0.0.0.0", "127.0.0.1"):
            self._record("suspicious_ip", ThreatLevel.MEDIUM, {"ip": ip}, source=ip)
            detected = True

        # Built-in: brute-force detection
        if self._check_brute_force(ip):
            self._record("brute_force", ThreatLevel.HIGH, {"ip": ip}, source=ip)
            detected = True

        # Built-in: XSS detection
        body = request.get("body", "")
        if isinstance(body, str) and self._detect_xss(body):
            self._record(
                "xss_attempt", ThreatLevel.HIGH, {"input": body[:50]}, source=ip
            )
            detected = True

        # Built-in: SQL injection detection
        if isinstance(body, str) and self._detect_injection(body):
            self._record(
                "sql_injection", ThreatLevel.CRITICAL, {"input": body[:50]}, source=ip
            )
            detected = True

        # Custom policies
        for policy in self.policies.values():
            if policy.check_fn and policy.check_fn(request):
                self._record(policy.threat_type, policy.level, request, source=ip)
                detected = True

        return detected

    def _check_brute_force(self, ip: str) -> bool:
        """Rate-based brute-force detection."""
        if not ip:
            return False
        now = time.time()
        timestamps = self._rate_counters.get(ip, [])
        timestamps = [t for t in timestamps if now - t < 60]
        timestamps.append(now)
        self._rate_counters[ip] = timestamps
        return len(timestamps) > self._brute_force_threshold

    def _detect_xss(self, text: str) -> bool:
        """Detect XSS patterns."""
        for pattern in self._xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_injection(self, text: str) -> bool:
        """Detect SQL injection patterns."""
        for pattern in self._injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    # ── Input Sanitization ───────────────────────────────────────

    def sanitize(self, text: str) -> str:
        """Remove XSS and injection patterns from input."""
        result = text
        # Remove HTML tags
        result = re.sub(r"<[^>]+>", "", result)
        # Remove javascript
        result = re.sub(r"javascript:", "", result, flags=re.IGNORECASE)
        # Remove event handlers
        result = re.sub(r"on\w+=", "", result, flags=re.IGNORECASE)
        return result.strip()

    # ── Integrity ────────────────────────────────────────────────

    def encrypt_sensitive(self, data: str) -> str:
        """SHA-256 hash of data."""
        return hashlib.sha256(data.encode()).hexdigest()

    def hmac_sign(self, data: str, key: str) -> str:
        """HMAC-SHA256 signature."""
        return hmac.new(key.encode(), data.encode(), hashlib.sha256).hexdigest()

    def verify_hmac(self, data: str, key: str, signature: str) -> bool:
        """Verify HMAC signature."""
        expected = self.hmac_sign(data, key)
        return hmac.compare_digest(expected, signature)

    # ── API Keys ────────────────────────────────────────────────

    def generate_api_key(self, name: str = "", expires_in: float = 0) -> str:
        """Generate a cryptographically random API key."""
        key = secrets.token_urlsafe(32)
        self.api_keys[key] = {
            "name": name,
            "created_at": time.time(),
            "expires_at": time.time() + expires_in if expires_in > 0 else None,
            "active": True,
        }
        return key

    def validate_api_key(self, key: str) -> bool:
        """Check if API key is valid and not expired."""
        info = self.api_keys.get(key)
        if info is None:
            return False
        if not info["active"]:
            return False
        return not (info["expires_at"] and time.time() > info["expires_at"])

    def revoke_api_key(self, key: str) -> None:
        """Revoke an API key."""
        info = self.api_keys.get(key)
        if info:
            info["active"] = False

    def rotate_api_key(self, old_key: str) -> str | None:
        """Rotate: revoke old key, generate new."""
        info = self.api_keys.get(old_key)
        if info is None:
            return None
        info["active"] = False
        new_key = self.generate_api_key(name=info["name"])
        return new_key

    # ── Threat Management ────────────────────────────────────────

    def resolve_threat(self, threat_type: str, source: str = "") -> int:
        """Mark matching threats as resolved."""
        count = 0
        for t in self.threats:
            if t.threat_type == threat_type and not t.resolved:
                if source and t.source != source:
                    continue
                t.resolved = True
                count += 1
        return count

    def get_threats(
        self, level: ThreatLevel | None = None, unresolved_only: bool = False
    ) -> list[ThreatEvent]:
        """Query threats."""
        result = self.threats
        if level:
            result = [t for t in result if t.level == level]
        if unresolved_only:
            result = [t for t in result if not t.resolved]
        return result

    # ── Audit ────────────────────────────────────────────────────

    def _record(
        self,
        threat_type: str,
        level: ThreatLevel,
        details: dict[str, Any],
        source: str = "",
    ) -> None:
        """Record a threat event."""
        self.threats.append(
            ThreatEvent(
                threat_type=threat_type, level=level, details=details, source=source
            )
        )

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_type: dict[str, int] = {}
        for t in self.threats:
            by_type[t.threat_type] = by_type.get(t.threat_type, 0) + 1
        unresolved = sum(1 for t in self.threats if not t.resolved)
        return {
            "threats_detected": len(self.threats),
            "unresolved": unresolved,
            "by_type": by_type,
            "api_keys": len(self.api_keys),
            "active_keys": sum(1 for v in self.api_keys.values() if v["active"]),
        }
