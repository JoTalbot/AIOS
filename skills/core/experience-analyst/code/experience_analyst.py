#!/usr/bin/env python3
"""Bounded read-only analyst for Octopus experience and reports.

Implements instruction #06 (learning) and vector УЧИТЬСЯ (#05):
- Scans experience/ and reports/ for lessons learned
- Extracts actionable insights
- Produces bounded improvement proposals
Read-only by default. Never modifies experience files directly.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE = Path(os.path.expanduser("~/agents/-Octopus"))
EXPERIENCE_DIR = BASE / "experience"
REPORTS_DIR = BASE / "reports"


def _read_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def scan_experience(limit: int = 50) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not EXPERIENCE_DIR.exists():
        return items
    for path in sorted(EXPERIENCE_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        if path.is_file() and path.suffix in {".md", ".txt", ""}:
            text = _read_safe(path)
            items.append({"path": str(path), "name": path.name, "size": path.stat().st_size, "preview": text[:300]})
    return items


def scan_reports(limit: int = 50) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not REPORTS_DIR.exists():
        return items
    for path in sorted(REPORTS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        if path.is_file() and path.suffix in {".md", ".txt", ".json"}:
            text = _read_safe(path)
            items.append({"path": str(path), "name": path.name, "size": path.stat().st_size, "preview": text[:300]})
    return items


def extract_keywords(texts: List[str], top_n: int = 20) -> List[Dict[str, Any]]:
    words: Counter = Counter()
    for text in texts:
        for token in re.findall(r"[A-Za-zа-яА-ЯёЁ]{3,}", text.lower()):
            words[token] += 1
    return [{"keyword": k, "count": v} for k, v in words.most_common(top_n)]


def run(_: str = "") -> Dict[str, Any]:
    experience = scan_experience()
    reports = scan_reports()
    all_texts = [item["preview"] for item in experience] + [item["preview"] for item in reports]
    keywords = extract_keywords(all_texts)
    score = 1000
    score -= max(0, 50 - len(experience)) * 5
    score -= max(0, 50 - len(reports)) * 2
    if not keywords:
        score -= 100
    grade = "S" if score >= 950 else "A" if score >= 900 else "B" if score >= 800 else "C" if score >= 600 else "D" if score >= 400 else "F"
    return {
        "skill": "experience-analyst",
        "timestamp": _now(),
        "score": score,
        "grade": grade,
        "status": "healthy" if grade in {"S", "A"} else "degraded" if grade in {"B", "C"} else "critical",
        "experience_count": len(experience),
        "reports_count": len(reports),
        "top_keywords": keywords[:20],
        "recent_experience": [{"name": e["name"], "preview": e["preview"][:120]} for e in experience[:10]],
        "recent_reports": [{"name": r["name"], "preview": r["preview"][:120]} for r in reports[:10]],
    }


if __name__ == "__main__":
    import sys
    payload = run(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
