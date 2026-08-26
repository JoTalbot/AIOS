"""AIOS Monitoring Dashboard Core.

Foundation layer for exposing runtime, agent, decision,
and benchmark observability data.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MonitoringSnapshot:
    """Current AIOS system snapshot."""

    metrics: Dict[str, Any] = field(default_factory=dict)


class DashboardCore:
    """Collects and serves monitoring information."""

    def __init__(self) -> None:
        self.snapshots: List[MonitoringSnapshot] = []

    def record(self, metrics: Dict[str, Any]) -> MonitoringSnapshot:
        snapshot = MonitoringSnapshot(metrics=metrics)
        self.snapshots.append(snapshot)
        return snapshot

    def latest(self) -> MonitoringSnapshot | None:
        if not self.snapshots:
            return None
        return self.snapshots[-1]

    def history(self) -> List[MonitoringSnapshot]:
        return self.snapshots
