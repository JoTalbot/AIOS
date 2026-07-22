"""AIOS Android Observability (M6).

Structured execution events, Prometheus metrics, and optional REST/web hooks for
Android automation actions and uiautomator failures.

M7 Enhancements:
- Heuristic-based failure prediction
- Process isolation for test reliability
- Enhanced telemetry with system metrics
"""

from __future__ import annotations

import json
import os
import psutil
import time
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple


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
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self._active_android_pid: Optional[int] = None
        self._heuristic_thresholds: Dict[str, float] = {
            "memory_mb": 500.0,
            "cpu_percent": 80.0,
            "event_rate": 100.0
        }

    def _isolate_process(self):
        """Isolate Android process for better monitoring."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    pinfo = proc.info
                    if pinfo.get('cmdline'):
                        cmdline_str = ' '.join(pinfo['cmdline'])
                        if 'dalvik' in cmdline_str or 'uiautomator' in cmdline_str:
                            self._active_android_pid = pinfo['pid']
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

    def check_heuristic_anomalies(self) -> List[Dict[str, Any]]:
        """Check for heuristic anomalies in system state."""
        anomalies = []
        
        try:
            memory = psutil.virtual_memory()
            if memory.used > self._heuristic_thresholds["memory_mb"] * 1024 * 1024:
                anomalies.append({
                    "type": "high_memory",
                    "value": memory.percent,
                    "threshold": self._heuristic_thresholds["memory_mb"]
                })
        except Exception:
            pass
        
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            if cpu > self._heuristic_thresholds["cpu_percent"]:
                anomalies.append({
                    "type": "high_cpu",
                    "value": cpu,
                    "threshold": self._heuristic_thresholds["cpu_percent"]
                })
        except Exception:
            pass
        
        return anomalies

    def predict_failure_risk(self) -> float:
        """Predict failure risk based on heuristics."""
        anomalies = self.check_heuristic_anomalies()
        if not anomalies:
            return 0.0
        
        risk_score = 0.0
        for anomaly in anomalies:
            if anomaly["type"] == "high_memory":
                risk_score += (anomaly["value"] - 50) / 50
            elif anomaly["type"] == "high_cpu":
                risk_score += (anomaly["value"] - 50) / 50
        
        return min(risk_score, 1.0)

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
        self.counters[f"android_{action}_total"] = self.counters.get(f"android_{action}_total", 0.0) + 1.0
        if not success:
            self.counters[f"android_{action}_failed"] = self.counters.get(f"android_{action}_failed", 0.0) + 1.0
        self.gauges["android_active_device"] = 1.0 if self.device_id else 0.0
        return event

    def to_prometheus(self) -> str:
        lines: List[str] = []
        for key, value in self.counters.items():
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {value}")
        for key, value in self.gauges.items():
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {value}")
        return "\n".join(lines)

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
            "metrics_prom": self.to_prometheus(),
        }

    def render_dashboard(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "events": len(self.events),
            "failure_rate": self.failure_rate(),
            "last_action": self.events[-1].action if self.events else None,
            "last_screen": self.events[-1].screen if self.events else None,
            "recent": [asdict(e) for e in self.events[-10:]],
            "failure_risk": self.predict_failure_risk(),
            "anomalies": self.check_heuristic_anomalies(),
        }