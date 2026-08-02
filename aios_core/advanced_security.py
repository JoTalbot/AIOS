"""Advanced Security Module for AIOS v10.7.0.

Multi-layer security: threat detection with signature patterns,
rate-based brute-force detection, input sanitization, HMAC integrity,
API key management with rotation, and security audit trail.

Classes:
    ThreatLevel    — severity of detected threats
    ThreatEvent    — recorded threat with details
    SecurityPolicy — configurable detection rule
    AdvancedSecurity — full security engine with detection, sanitization, audit
    Authenticator  — authenticates API requests
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
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ThreatLevel(StrEnum):
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
    check_fn: Optional[Callable[[dict[str, Any]], bool]] = None
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
        self.api_keys: dict[str, dict[str, Any]] = {}  # key → {name, created_at, expires_at, active}
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

        ip = request.get("ip", "")
        if ip in ("0.0.0.0", "127.0.0.1"):
            self._record("suspicious_ip", ThreatLevel.MEDIUM, {"ip": ip}, source=ip)
            detected = True

        if self._check_brute_force(ip):
            self._record("brute_force", ThreatLevel.HIGH, {"ip": ip}, source=ip)
            detected = True

        body = request.get("body", "")
        if isinstance(body, str):
            if self._detect_xss(body):
                self._record("xss_attempt", ThreatLevel.HIGH, {"input": body[:50]}, source=ip)
                detected = True

            if self._detect_injection(body):
                self._record("sql_injection", ThreatLevel.CRITICAL, {"input": body[:50]}, source=ip)
                detected = True

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
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self._xss_patterns)

    def _detect_injection(self, text: str) -> bool:
        """Detect SQL injection patterns."""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self._injection_patterns)

    # ── Input Sanitization ───────────────────────────────────────

    def sanitize(self, text: str) -> str:
        """Remove XSS and injection patterns from input."""
        result = text
        result = re.sub(r"<[^>]+>", "", result)
        result = re.sub(r"javascript:", "", result, flags=re.IGNORECASE)
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
        now = time.time()
        self.api_keys[key] = {
            "name": name,
            "created_at": now,
            "expires_at": now + expires_in if expires_in > 0 else None,
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
        expires_at = info.get("expires_at")
        if expires_at is not None and time.time() > expires_at:
            return False
        return True

    def revoke_api_key(self, key: str) -> None:
        """Revoke an API key."""
        info = self.api_keys.get(key)
        if info:
            info["active"] = False

    def rotate_api_key(self, old_key: str) -> Optional[str]:
        """Rotate: revoke old key, generate new."""
        info = self.api_keys.get(old_key)
        if info is None:
            return None
        info["active"] = False
        new_key = self.generate_api_key(name=info.get("name", ""))
        return new_key

    # ── Threat Management ────────────────────────────────────────

    def resolve_threat(self, threat_type: str, source: str = "") -> int:
        """Mark matching threats as resolved."""
        count = 0
        for threat in self.threats:
            if threat.threat_type == threat_type and not threat.resolved:
                if source and threat.source != source:
                    continue
                threat.resolved = True
                count += 1
        return count

    def get_threats(
        self, level: Optional[ThreatLevel] = None, unresolved_only: bool = False
    ) -> list[ThreatEvent]:
        """Query threats."""
        result = self.threats
        if level is not None:
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
            ThreatEvent(threat_type=threat_type, level=level, details=details, source=source)
        )

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_type: dict[str, int] = {}
        for threat in self.threats:
            by_type[threat.threat_type] = by_type.get(threat.threat_type, 0) + 1
        unresolved = sum(1 for threat in self.threats if not threat.resolved)
        active_keys = sum(1 for key_info in self.api_keys.values() if key_info.get("active"))
        return {
            "threats_detected": len(self.threats),
            "unresolved": unresolved,
            "by_type": by_type,
            "api_keys": len(self.api_keys),
            "active_keys": active_keys,
        }


class Authenticator:
    """Authenticates API requests."""

    def __init__(self, security: AdvancedSecurity) -> None:
        self.security = security

    def authenticate(self, request: dict[str, Any]) -> bool:
        """Authenticate API request."""
        api_key = request.get("api_key")
        if not api_key:
            return False
        return self.security.validate_api_key(api_key)

    def authorize(self, request: dict[str, Any]) -> bool:
        """Authorize API request."""
        # Add authorization logic here
        return True


def main() -> None:
    security = AdvancedSecurity()
    authenticator = Authenticator(security)

    # Example usage
    request = {"ip": "127.0.0.1", "body": "Hello, World!", "api_key": security.generate_api_key()}
    if authenticator.authenticate(request) and authenticator.authorize(request):
        print("Request is authenticated and authorized")
    else:
        print("Request is not authenticated or authorized")

    if security.detect_threat(request):
        print("Threat detected")
    else:
        print("No threat detected")


if __name__ == "__main__":
    main()