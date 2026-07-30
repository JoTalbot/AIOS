#!/usr/bin/env python3
"""Bounded-read-only strict iteration archive gate.

Enforces strict iteration archive policies.
Read-only by default.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(os.path.expanduser("~/agents/-Octopus"))
LOGS_DIR = BASE / "logs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_archive() -> Dict[str, Any]:
    logs = []
    if LOGS_DIR.exists():
        for p in sorted(LOGS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            if p.is_file() and p.suffix == ".md":
                logs.append({"name": p.name, "size": p.stat().st_size})
    return {"logs": logs, "count": len(logs)}


def run(_: str = "") -> Dict[str, Any]:
    archive = check_archive()
    score = 1000
    score -= max(0, 10 - archive["count"]) * 10
    grade = "S" if score >= 950 else "A" if score >= 900 else "B" if score >= 800 else "C" if score >= 600 else "D" if score >= 400 else "F"
    return {
        "skill": "strict-iter-archive-gate",
        "timestamp": _now(),
        "score": score,
        "grade": grade,
        "status": "healthy" if grade in {"S", "A"} else "degraded" if grade in {"B", "C"} else "critical",
        "archive": archive,
    }


if __name__ == "__main__":
    import sys
    payload = run(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
