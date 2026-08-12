"""Redacted recovery SLO state shared by Colab automation and monitoring."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

DEFAULT_STATE = Path(__file__).resolve().parents[1] / "data" / "colab_recovery_metrics.json"
SLO_SECONDS = {
    "endpoint_reuse": 15.0,
    "hot_failover": 30.0,
    "tunnel_only": 60.0,
    "runtime_restart": 120.0,
    "full_cold": 600.0,
}


def record_recovery(
    *,
    mode: str,
    duration_seconds: float,
    success: bool,
    error_class: str = "",
    path: Path = DEFAULT_STATE,
) -> dict:
    normalized = mode if mode in SLO_SECONDS else "full_cold"
    duration = max(0.0, float(duration_seconds))
    slo = SLO_SECONDS[normalized]
    payload = {
        "version": 1,
        "timestamp": time.time(),
        "mode": normalized,
        "success": bool(success),
        "duration_seconds": round(duration, 3),
        "slo_seconds": slo,
        "slo_met": bool(success and duration <= slo),
        "error_class": str(error_class)[:80] if error_class else "",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return payload
