"""AIOS Telemetry / OpenTelemetry Support (v4.2)"""

from typing import Optional
import time


class Telemetry:
    """Simple telemetry collector (placeholder for real OpenTelemetry)."""

    def __init__(self):
        self.metrics = {}
        self.traces = []

    def record_metric(self, name: str, value: float, tags: Optional[dict] = None):
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append({"value": value, "tags": tags or {}, "ts": time.time()})

    def start_trace(self, name: str):
        trace_id = f"trace_{len(self.traces)}"
        self.traces.append({"id": trace_id, "name": name, "start": time.time()})
        return trace_id

    def end_trace(self, trace_id: str):
        for trace in self.traces:
            if trace["id"] == trace_id:
                trace["end"] = time.time()
                trace["duration"] = trace["end"] - trace["start"]
                break

    def stats(self) -> dict:
        return {
            "metrics_collected": len(self.metrics),
            "traces": len(self.traces)
        }


telemetry = Telemetry()