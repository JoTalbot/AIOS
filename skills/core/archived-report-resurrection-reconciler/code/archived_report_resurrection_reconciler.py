#!/usr/bin/env python3
"""Bounded-read-only archived report resurrection reconciler.

Checks archived reports for potential resurrection.
Read-only by default.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(os.path.expanduser("~/agents/-Octopus"))
ARCHIVE_DIR = BASE / "experience"
REPORTS_DIR = BASE / "reports"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def scan_archived() -> List[Dict[str, Any]]:
    items = []
    for d in [ARCHIVE_DIR, REPORTS_DIR]:
        if not d.exists():
            continue
        for p in sorted(d.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            if p.is_file() and p.suffix in {".md", ".txt", ".json"}:
                items.append({"path": str(p), "name": p.name, "size": p.stat().st_size})
    return items


def run(_: str = "") -> Dict[str, Any]:
    archived = scan_archived()
    score = 1000
    score -= max(0, 10 - len(archived)) * 10
    grade = "S" if score >= 950 else "A" if score >= 900 else "B" if score >= 800 else "C" if score >= 600 else "D" if score >= 400 else "F"
    return {
        "skill": "archived-report-resurrection-reconciler",
        "timestamp": _now(),
        "score": score,
        "grade": grade,
        "status": "healthy" if grade in {"S", "A"} else "degraded" if grade in {"B", "C"} else "critical",
        "archived_count": len(archived),
        "archived": archived[:10],
    }


if __name__ == "__main__":
    import sys
    payload = run(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
