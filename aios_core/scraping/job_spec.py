#!/usr/bin/env python3
"""
AIOS Scraper Farm - Спецификация задач скрапинга (Этап 5)

Описывает структуру задания и очереди заданий, которые VPS отправляет
Colab-нодам. Задание = JSON-документ.

Пример задания:
{
  "job_id": "airdrops-2026-08-10-001",
  "kind": "scrape",
  "source": "airdrops",
  "target": "https://airdrops.io/",
  "collect": ["url", "title", "deadline", "ticker"],
  "params": {"max_pages": 3, "headless": true},
  "created_at": "...",
  "status": "pending"
}

kinds: airdrops | cryptopanic | freelancehunt | dex | news | generic
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE_DIR = REPO_ROOT / "data" / "scraping"

KINDS = {"airdrops", "cryptopanic", "freelancehunt", "dex", "news", "generic"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_job(
    source: str,
    target: str,
    collect: Optional[list[str]] = None,
    params: Optional[dict] = None,
    job_id: Optional[str] = None,
) -> dict:
    if source not in KINDS and source != "generic":
        # разрешаем произвольные имена, но предупреждаем
        pass
    return {
        "job_id": job_id or f"{source}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}",
        "kind": "scrape",
        "source": source,
        "target": target,
        "collect": collect or ["url", "title"],
        "params": params or {"max_pages": 1, "headless": True},
        "created_at": _now(),
        "status": "pending",
    }


def save_job(job: dict, queue_dir: Optional[Path] = None) -> Path:
    d = Path(queue_dir or QUEUE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{job['job_id']}.json"
    p.write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def list_pending(queue_dir: Optional[Path] = None) -> list[dict]:
    d = Path(queue_dir or QUEUE_DIR)
    if not d.exists():
        return []
    out = []
    for p in d.glob("*.json"):
        try:
            job = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if job.get("status") == "pending":
            out.append(job)
    return out


def mark(job_id: str, status: str, queue_dir: Optional[Path] = None) -> bool:
    d = Path(queue_dir or QUEUE_DIR)
    p = d / f"{job_id}.json"
    if not p.exists():
        return False
    job = json.loads(p.read_text(encoding="utf-8"))
    job["status"] = status
    if status in ("running", "done", "error"):
        job["updated_at"] = _now()
    p.write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    return True
