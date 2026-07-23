"""Advanced Observability for AIOS (OpenTelemetry compatible)"""

import time
from typing import Any, Dict


class Observability:
    """Unified observability: metrics, traces, logs."""

    def __init__(self):
        self.metrics: Dict[str, float] = {}
        self.traces: list = []
        self.logs: list = []

    def record_metric(self, name: str, value: float, labels: Dict = None) -> None:
        """Execute record metric."""
        key = f"{name}_{labels}" if labels else name
        self.metrics[key] = value

    def start_trace(self, name: str, attributes: Dict = None) -> str:
        """Execute start trace."""
        trace_id = f"trace_{len(self.traces)}"
        self.traces.append(
            {
                "id": trace_id,
                "name": name,
                "start": time.time(),
                "attributes": attributes or {},
            }
        )
        return trace_id

    def end_trace(self, trace_id: str) -> None:
        """Execute end trace."""
        for trace in self.traces:
            if trace["id"] == trace_id and "end" not in trace:
                trace["end"] = time.time()
                trace["duration_ms"] = (trace["end"] - trace["start"]) * 1000
                break

    def log(self, level: str, message: str, **kwargs) -> None:
        """Execute log."""
        self.logs.append({"level": level, "message": message, "timestamp": time.time(), **kwargs})

    def export_prometheus(self) -> str:
        """Execute export prometheus."""
        lines = []
        for name, value in self.metrics.items():
            lines.append(f'{name.replace(" ", "_")} {value}')
        return "\n".join(lines)

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "metrics": len(self.metrics),
            "traces": len(self.traces),
            "logs": len(self.logs),
        }


observability = Observability()
