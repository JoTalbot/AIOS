"""Zero Trust Security for AIOS v10.5.0.

Never trust, always verify — continuous authentication, device trust
scoring, network segmentation, policy engine, and audit trail.

Classes:
    TrustLevel      — trust score enum (UNTRUSTED..FULLY_TRUSTED)
    DeviceProfile   — device identity + trust attributes
    TrustPolicy     — access rule with conditions and minimum trust
    TrustEngine     — evaluates context against policies
    ZeroTrust       — backward-compatible façade (add_policy/verify/stats)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class TrustLevel(int, Enum):
    """Trust score 0–100 mapped to discrete levels."""

    UNTRUSTED = 0
    LOW = 25
    MEDIUM = 50
    HIGH = 75
    FULLY_TRUSTED = 100


# ── Device Profile ───────────────────────────────────────────────────────────


@dataclass
class DeviceProfile:
    """Device identity with trust attributes."""

    device_id: str
    user_id: str = ""
    platform: str = ""
    ip_address: str = ""
    fingerprint: str = ""
    trust_score: float = 0.0
    last_verified: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)

    def compute_trust(self) -> float:
        """Compute trust score from attributes."""
        score = 0.0
        if self.fingerprint:
            score += 20.0
        if self.platform in ("rozetka", "olx", "prom"):
            score += 15.0
        if self.ip_address and not self.ip_address.startswith("10."):
            score += 10.0
        if self.attributes.get("verified_device"):
            score += 25.0
        if self.attributes.get("mfa_enabled"):
            score += 30.0
        self.trust_score = min(score, 100.0)
        self.last_verified = time.time()
        return self.trust_score

    def trust_level(self) -> TrustLevel:
        """Map numeric score to TrustLevel enum."""
        if self.trust_score >= 100:
            return TrustLevel.FULLY_TRUSTED
        if self.trust_score >= 75:
            return TrustLevel.HIGH
        if self.trust_score >= 50:
            return TrustLevel.MEDIUM
        if self.trust_score >= 25:
            return TrustLevel.LOW
        return TrustLevel.UNTRUSTED


# ── Trust Policy ─────────────────────────────────────────────────────────────


@dataclass
class TrustPolicy:
    """Access rule: resource + required trust level + conditions."""

    name: str
    resource: str
    min_trust_level: TrustLevel = TrustLevel.MEDIUM
    conditions: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Check if context meets all conditions."""
        # Trust level gate
        trust = context.get("trust_level", TrustLevel.UNTRUSTED)
        if isinstance(trust, (int, float)):
            trust = TrustLevel(min(int(trust), 100))
        if trust < self.min_trust_level:
            return False
        # Additional conditions
        for key, expected in self.conditions.items():
            actual = context.get(key)
            if actual is None:
                return False
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, dict):
                # nested match
                for sk, sv in expected.items():
                    if actual.get(sk) != sv:
                        return False
            else:
                if actual != expected:
                    return False
        return True


# ── Trust Engine ─────────────────────────────────────────────────────────────


class TrustEngine:
    """Core trust evaluation engine with device registry and audit."""

    def __init__(self) -> None:
        self.devices: dict[str, DeviceProfile] = {}
        self.policies: dict[str, TrustPolicy] = {}
        self.audit_log: list[dict[str, Any]] = []

    # ── Device Management ────────────────────────────────────────

    def register_device(self, profile: DeviceProfile) -> None:
        """Register a device profile."""
        profile.compute_trust()
        self.devices[profile.device_id] = profile

    def get_device(self, device_id: str) -> DeviceProfile | None:
        """Return device profile."""
        return self.devices.get(device_id)

    def verify_device(self, device_id: str) -> float:
        """Re-verify device trust score."""
        profile = self.devices.get(device_id)
        if profile is None:
            return 0.0
        return profile.compute_trust()

    def revoke_device(self, device_id: str) -> None:
        """Remove device from trusted registry."""
        if device_id in self.devices:
            self.devices[device_id].trust_score = 0.0
            self.devices[device_id].trust_level = TrustLevel.UNTRUSTED

    # ── Policy Management ────────────────────────────────────────

    def add_policy(self, policy: TrustPolicy) -> None:
        """Add an access policy."""
        self.policies[policy.name] = policy
        self._audit("add_policy", {"policy": policy.name, "resource": policy.resource})

    def remove_policy(self, name: str) -> None:
        """Remove a policy."""
        del self.policies[name]
        self._audit("remove_policy", {"policy": name})

    # ── Evaluation ───────────────────────────────────────────────

    def verify(self, context: dict[str, Any]) -> bool:
        """Verify access against ALL registered policies.

        All applicable policies must pass for access to be granted.
        """
        if not context.get("authenticated"):
            self._audit("verify_denied", {"reason": "not_authenticated"})
            return False

        # Build trust context from device if available
        device_id = context.get("device_id", "")
        if device_id and device_id in self.devices:
            device = self.devices[device_id]
            context["trust_level"] = device.trust_level()
            context["trust_score"] = device.trust_score

        # Check each applicable policy
        target_resource = context.get("resource", "*")
        for policy in self.policies.values():
            if policy.resource == "*" or policy.resource == target_resource:
                if not policy.evaluate(context):
                    self._audit(
                        "verify_denied",
                        {"policy": policy.name, "resource": target_resource},
                    )
                    return False

        context["authorized"] = True
        self._audit("verify_granted", {"resource": target_resource})
        return True

    # ── Network Segmentation ─────────────────────────────────────

    def check_network_segment(self, ip: str, allowed_segments: list[str]) -> bool:
        """Check if IP belongs to an allowed network segment."""
        import ipaddress

        try:
            addr = ipaddress.ip_address(ip)
            for seg in allowed_segments:
                network = ipaddress.ip_network(seg, strict=False)
                if addr in network:
                    return True
        except ValueError:
            pass
        return False

    # ── Audit ────────────────────────────────────────────────────

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent audit events."""
        return self.audit_log[-limit:]

    def _audit(self, action: str, details: dict[str, Any]) -> None:
        self.audit_log.append({"action": action, "timestamp": time.time(), **details})

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        trust_levels = {}
        for d in self.devices.values():
            level = d.trust_level().name
            trust_levels[level] = trust_levels.get(level, 0) + 1
        return {
            "devices": len(self.devices),
            "policies": len(self.policies),
            "trust_levels": trust_levels,
            "audit_events": len(self.audit_log),
        }


# ── Backward-compatible façade ──────────────────────────────────────────────


class ZeroTrust:
    """Backward-compatible façade preserving add_policy/verify/stats API."""

    def __init__(self) -> None:
        self.policies: dict[str, dict] = {}
        self._engine: TrustEngine = TrustEngine()

    def add_policy(self, name: str, rules: dict) -> None:
        """Add policy (dict-based for backward compat)."""
        self.policies[name] = rules
        # Also register in engine
        resource = rules.get("resource", "*")
        min_trust = TrustLevel(rules.get("min_trust", 50))
        conditions = {
            k: v for k, v in rules.items() if k not in ("resource", "min_trust")
        }
        self._engine.add_policy(
            TrustPolicy(
                name=name,
                resource=resource,
                min_trust_level=min_trust,
                conditions=conditions,
            )
        )

    def verify(self, context: dict) -> bool:
        """Verify access (backward-compatible)."""
        if context.get("authenticated") and context.get("authorized"):
            return True
        # Also check engine policies
        return self._engine.verify(context)

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"policies": len(self.policies)}

    def engine(self) -> TrustEngine:
        """Access the underlying TrustEngine."""
        return self._engine
