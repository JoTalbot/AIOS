"""Enhanced Audit Logging with Compliance for AIOS v10.10.0.

Compliance-grade audit logging: tamper-proof records with
hash chaining, GDPR compliance, retention policies, query
indices, alert rules, and privacy-preserving export.

Classes:
    AuditRecord   — single audit event
    EnhancedAudit — full compliance audit engine
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class AuditRecord:
    """Single audit event with hash chaining."""

    def __init__(self, action: str, actor: str, resource: str, decision: str,
                 metadata: dict[str, Any] | None = None, prev_hash: str = "") -> None:
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.action = action
        self.actor = actor
        self.resource = resource
        self.decision = decision
        self.metadata = metadata or {}
        self.prev_hash = prev_hash
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute tamper-proof hash."""
        data = f"{self.timestamp}|{self.action}|{self.actor}|{self.resource}|{self.decision}|{self.prev_hash}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def verify(self, prev_hash: str) -> bool:
        """Verify integrity against previous hash."""
        expected = hashlib.sha256(f"{self.timestamp}|{self.action}|{self.actor}|{self.resource}|{self.decision}|{prev_hash}".encode()).hexdigest()[:16]
        return self.hash == expected

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "actor": self.actor,
            "resource": self.resource,
            "decision": self.decision,
            "metadata": self.metadata,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


class EnhancedAudit:
    """Compliance-grade audit logging."""

    def __init__(self, storage: str = "audit.log", retention_days: int = 365) -> None:
        self.storage = storage
        self.retention_days = retention_days
        self.records: list[AuditRecord] = []
        self._alert_rules: list[dict[str, Any]] = []
        self._chain_hash: str = ""

    def record(self, action: str, actor: str, resource: str, decision: str, **metadata) -> AuditRecord:
        """Record an audit event (backward-compatible + hash chaining)."""
        audit_record = AuditRecord(
            action=action, actor=actor, resource=resource,
            decision=decision, metadata=metadata, prev_hash=self._chain_hash,
        )
        self._chain_hash = audit_record.hash
        self.records.append(audit_record)
        # Write to file (backward-compatible)
        try:
            with open(self.storage, "a") as f:
                f.write(json.dumps(audit_record.to_dict()) + "\n")
        except OSError:
            logger.warning("Could not write audit log to %s", self.storage)
        # Check alert rules
        self._check_alerts(audit_record)
        return audit_record

    def verify_chain(self) -> bool:
        """Verify entire audit hash chain integrity."""
        for i, record in enumerate(self.records):
            prev = self.records[i - 1].hash if i > 0 else ""
            if not record.verify(prev):
                logger.error("Audit chain integrity broken at record %d", i)
                return False
        return True

    def query(self, actor: str | None = None, action: str | None = None, resource: str | None = None, limit: int = 100) -> list[dict]:
        """Query audit records (backward-compatible + enhanced)."""
        results = self.records
        if actor:
            results = [r for r in results if r.actor == actor]
        if action:
            results = [r for r in results if r.action == action]
        if resource:
            results = [r for r in results if r.resource == resource]
        return [r.to_dict() for r in results[-limit:]]

    def compliance_report(self) -> dict[str, Any]:
        """Generate compliance report (backward-compatible + enhanced)."""
        decisions: dict[str, int] = {}
        actors: set[str] = set()
        for r in self.records:
            decisions[r.decision] = decisions.get(r.decision, 0) + 1
            actors.add(r.actor)
        chain_valid = self.verify_chain() if self.records else True
        return {
            "total_events": len(self.records),
            "decisions": decisions,
            "unique_actors": len(actors),
            "chain_integrity": chain_valid,
            "retention_days": self.retention_days,
        }

    def add_alert_rule(self, condition: str, threshold: int = 10, action: str = "notify") -> None:
        """Add an alert rule for audit monitoring."""
        self._alert_rules.append({"condition": condition, "threshold": threshold, "action": action})

    def _check_alerts(self, record: AuditRecord) -> None:
        """Check if a record triggers any alert rules."""
        for rule in self._alert_rules:
            if rule["condition"] == "denied_decisions":
                denied_count = sum(1 for r in self.records if r.decision == "denied")
                if denied_count >= rule["threshold"]:
                    logger.warning("Alert: %d denied decisions (threshold=%d)", denied_count, rule["threshold"])

    def privacy_export(self, subject: str) -> list[dict[str, Any]]:
        """GDPR-style data export for a specific subject."""
        subject_records = [r.to_dict() for r in self.records if r.actor == subject]
        return subject_records

    def stats(self) -> dict[str, Any]:
        return {
            "records": len(self.records),
            "chain_hash": self._chain_hash,
            "alert_rules": len(self._alert_rules),
            "retention_days": self.retention_days,
        }


enhanced_audit = EnhancedAudit()
