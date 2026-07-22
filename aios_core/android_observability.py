"""AIOS Android Observability (M6).

Emits structured execution events through existing telemetry/logging surface.
Each tap, type, swipe, and action becomes a trace/log event with latency,
screen context, and package info.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class AndroidExecutionEvent:
    timestamp: float
    package: str
    device_id: str
    action: str
    latency_ms: float
    screen: Optional[str]
    success: bool
    meta: Dict[str, Any]


class AndroidObservability:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.events: List[AndroidExecutionEvent] = []

    def record(self, package: str, action: str, latency_ms: float, success: bool, screen: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
        event = AndroidExecutionEvent(
            timestamp=time.time(),
            package=package,
            device_id=self.device_id,
            action=action,
            latency_ms=latency_ms,
            screen=screen,
            success=success,
            meta=meta or {},
        )
        self.events.append(event)
        try:
            print(json.dumps(asdict(event), ensure_ascii=False))
        except Exception:
            pass
        return event

    def failure_rate(self, action: Optional[str] = None) -> float:
        subset = self.events
        if action:
            subset = [e for e in subset if e.action == action]
        if not subset:
            return 0.0
        return sum(1 for e in subset if not e.success) / len(subset)

    def summary(self) -> Dict[str, Any]:
        total = len(self.events)
        failed = sum(1 for event in self.events if not event.success)
        return {
            "events": total,
            "failed": failed,
            "failure_rate": failed / total if total else 0.0,
            "last_screen": self.events[-1].screen if self.events else None,
        }
