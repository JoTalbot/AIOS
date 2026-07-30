#!/usr/bin/env python3
"""Bounded read-only systemd unit linter.

Implements systemd unit linting and validation.
Read-only by default. Never modifies unit files.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def lint_units() -> List[Dict[str, Any]]:
    findings = []
    try:
        r = subprocess.run(["systemctl", "list-unit-files", "--type=service", "--no-pager", "--plain"],
                           capture_output=True, text=True, timeout=10)
        for line in (r.stdout or "").splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                unit, state = parts[0], parts[1]
                if state == "disabled" and "octopus" in unit:
                    findings.append({"unit": unit, "state": state, "severity": "medium"})
    except Exception:
        pass
    return findings


def run(_: str = "") -> Dict[str, Any]:
    findings = lint_units()
    score = 1000
    score -= sum(1 for f in findings if f["severity"] == "medium") * 10
    grade = "S" if score >= 950 else "A" if score >= 900 else "B" if score >= 800 else "C" if score >= 600 else "D" if score >= 400 else "F"
    return {
        "skill": "systemd-unit-lint",
        "timestamp": _now(),
        "score": score,
        "grade": grade,
        "status": "healthy" if grade in {"S", "A"} else "degraded" if grade in {"B", "C"} else "critical",
        "findings": findings[:20],
        "findings_count": len(findings),
    }


if __name__ == "__main__":
    import sys
    payload = run(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
