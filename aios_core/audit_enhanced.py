"""Enhanced Audit Logging with Compliance"""

import json
from datetime import datetime
from typing import Any, Dict, List


class EnhancedAudit:
    """Compliance-grade audit logging."""

    def __init__(self, storage: str = "audit.log"):
        self.storage = storage
        self.records: List[Dict] = []

    def record(self, action: str, actor: str, resource: str, decision: str, **metadata) -> None:
        """Execute record."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "actor": actor,
            "resource": resource,
            "decision": decision,
            "metadata": metadata,
        }
        self.records.append(record)
        with open(self.storage, "a") as f:
            f.write(json.dumps(record) + "\n")

    def query(self, actor: str = None, action: str = None, limit: int = 100) -> List[Dict]:
        """Execute query."""
        results = self.records
        if actor:
            results = [r for r in results if r["actor"] == actor]
        if action:
            results = [r for r in results if r["action"] == action]
        return results[-limit:]

    def compliance_report(self) -> dict:
        """Execute compliance report."""
        decisions = {}
        for r in self.records:
            d = r["decision"]
            decisions[d] = decisions.get(d, 0) + 1
        return {"total_events": len(self.records), "decisions": decisions}


enhanced_audit = EnhancedAudit()
