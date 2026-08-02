#!/usr/bin/env python3
"""GitHub Issues → бэклог автокодера (п.5 плана, GitHub-интеграция вместо MCP).

Тянет открытые issue с меткой `auto-coder` (fallback: любые открытые с [auto]
в заголовке) и добавляет их в data/coder_backlog.json как pending-задачи.
Дедупликация по "#<номер>" в описании. Комментарий-чекбокс: задача берётся
планировщиком в порядке приоритета (bug/security вперёд — ранжирование в phase_plan).

Использование: sync_gh_issues.py [--dry-run]
Периодичность: aios-gh-issues.timer (ежедневно 04:15).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

REPO = os.environ.get("AIOS_REPO_PATH", "/root/AIOS")
BACKLOG = os.path.join(REPO, "data", "coder_backlog.json")
REPO_SLUG = os.environ.get("AIOS_GH_REPO", "JoTalbot/AIOS")
TOKEN = os.environ.get("GITHUB_API_KEY") or os.environ.get("GITHUB_TOKEN", "")


def fetch_issues() -> list[dict]:
    out = []
    for query in ("labels=auto-coder&state=open", "state=open&per_page=30"):
        url = f"https://api.github.com/repos/{REPO_SLUG}/issues?{query}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "aios-coder",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                items = json.loads(r.read().decode())
            for it in items:
                if "pull_request" in it:
                    continue
                if query.startswith("state") and "[auto]" not in (it.get("title") or ""):
                    continue  # второй заход — только явно помеченные [auto]
                out.append({"number": it["number"], "title": it.get("title", ""),
                            "labels": [l["name"] for l in it.get("labels", [])]})
        except Exception as e:
            print(f"github api ({query[:20]}…): {e}")
    uniq = {i["number"]: i for i in out}
    return list(uniq.values())


def prio_of(title: str, labels: list[str]) -> str:
    t = title.lower()
    if "critical" in t or "security" in t or "уязвим" in t:
        return "high"
    if "bug" in labels or "fix" in t or "bug" in t:
        return "medium"
    return "low"


def main() -> int:
    dry = "--dry-run" in sys.argv
    try:
        backlog = json.load(open(BACKLOG, encoding="utf-8"))
    except Exception:
        backlog = {"tasks": [], "history": [], "cycle_count": 0}
    tasks = backlog.setdefault("tasks", [])
    existing = " ".join(str(t.get("description", "")) for t in tasks)

    issues = fetch_issues()
    added = 0
    for it in issues:
        tag = f"#{it['number']}"
        if tag in existing:
            continue
        desc = f"[GitHub {tag}] {it['title'].strip()}"
        print(("+" if not dry else "[dry] +") + f" {desc} (prio={prio_of(it['title'], it['labels'])})")
        if not dry:
            tasks.append({
                "description": desc,
                "priority": prio_of(it["title"], it["labels"]),
                "created": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            })
            added += 1
    if not dry:
        with open(BACKLOG, "w", encoding="utf-8") as fh:
            json.dump(backlog, fh, indent=2, ensure_ascii=False)
    print(f"Готово: issues найдено {len(issues)}, добавлено {added}, всего задач {len(tasks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
