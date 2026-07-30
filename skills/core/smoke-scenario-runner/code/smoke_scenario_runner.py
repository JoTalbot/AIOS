#!/usr/bin/env python3
"""Bounded read-only smoke scenario runner.

Implements smoke test scenario runner.
Read-only by default. Never modifies system state.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(os.path.expanduser("~/agents/-Octopus"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_smoke_checks() -> Dict[str, Any]:
    checks = []
    try:
        r = subprocess.run(["systemctl", "is-active", "ollama.service"], capture_output=True, text=True, timeout=5)
        checks.append({"check": "ollama_active", "passed": r.stdout.strip() == "active"})
    except Exception:
        checks.append({"check": "ollama_active", "passed": False})
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        checks.append({"check": "docker_available", "passed": r.returncode == 0})
    except Exception:
        checks.append({"check": "docker_available", "passed": False})
    return {"checks": checks, "passed": sum(1 for c in checks if c["passed"]), "total": len(checks)}


def run(_: str = "") -> Dict[str, Any]:
    smoke = run_smoke_checks()
    score = 1000
    if smoke["total"] > 0:
        score = int((smoke["passed"] / smoke["total"]) * 1000)
    grade = "S" if score >= 950 else "A" if score >= 900 else "B" if score >= 800 else "C" if score >= 600 else "D" if score >= 400 else "F"
    return {
        "skill": "smoke-scenario-runner",
        "timestamp": _now(),
        "score": score,
        "grade": grade,
        "status": "healthy" if grade in {"S", "A"} else "degraded" if grade in {"B", "C"} else "critical",
        "smoke": smoke,
    }


if __name__ == "__main__":
    import sys
    payload = run(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
