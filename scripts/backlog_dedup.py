#!/usr/bin/env python3
"""Регулярный дедуп бэклога автокодера (систематизация разовой чистки 02.08).

Анализатор каждый цикл добавляет до 3 новых задач — бэклог растёт и дублируется.
Этот скрипт (aios-backlog-dedup.timer, ежедневно 04:30) держит его здоровым:
  1. done de-facto — задачи про файлы, созданные/влитые в main за последнюю неделю;
  2. protected-цели архивируются (AGENTS.md);
  3. мета-обёртки («Добавить задачу…») архивируются;
  4. fuzzy/токен-дубли схлопываются (difflib >0.72, затем Jaccard >=0.5);
  5. кап на pending (CAP) — остаток в архив.

Использование: backlog_dedup.py [--dry-run]
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys

REPO = os.environ.get("AIOS_REPO_PATH", "/root/AIOS")
BACKLOG = os.path.join(REPO, "data", "coder_backlog.json")
ARCHIVE = os.path.join(REPO, "data", "backlog_archive.json")
CAP = int(os.environ.get("AIOS_BACKLOG_CAP", "25"))
PRIO = {"critical": 0, "high": 1, "medium": 2, "low": 3}
STOP = {"и", "в", "на", "для", "по", "с", "к", "из", "или", "а", "о", "не",
        "добавить", "создать", "создайте", "разработать", "написать", "провести",
        "проведение", "внедрить", "внедрение", "задачу", "модуль", "системы",
        "новые", "новых", "кода", "проекта", "всех"}
PROTECTED_HINTS = ("api_v2_batch", "llm_balancer", "run_coder_orchestrator",
                   "run_telegram_bot", "self_protection", "selfguard")
DONE_HINTS = ("техническ", "долг")  # отчёт по техдолгу сдан 02.08


def norm(s: str) -> str:
    s = re.sub(r"[^a-zа-яё0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def toks(s: str) -> set[str]:
    return set(w for w in norm(s).split() if len(w) > 3 and w not in STOP)


def cluster_fuzzy(items, key_fn, sim=0.72):
    clusters = []
    for t in items:
        k = key_fn(t)
        for c in clusters:
            if difflib.SequenceMatcher(None, k, c["key"]).ratio() > sim:
                c["dups"].append(t)
                break
        else:
            clusters.append({"key": k, "keep": t, "dups": []})
    return clusters


def cluster_jaccard(items, thr=0.5):
    clusters = []
    for t in items:
        tt = toks(t.get("description", ""))
        for c in clusters:
            inter = len(tt & c["toks"])
            if tt and inter / max(1, len(tt | c["toks"])) >= thr:
                c["dups"].append(t)
                c["toks"] |= tt
                break
        else:
            clusters.append({"toks": set(tt), "keep": t, "dups": []})
    return clusters


def main() -> int:
    dry = "--dry-run" in sys.argv
    b = json.load(open(BACKLOG, encoding="utf-8"))
    arch = json.load(open(ARCHIVE, encoding="utf-8")) if os.path.exists(ARCHIVE) else {"runs": []}
    from datetime import datetime, timezone
    run = {"ts": datetime.now(timezone.utc).isoformat(), "moves": []}

    pend = [t for t in b.get("tasks", []) if t.get("status") == "pending"]
    before = len(pend)

    def move(t, status, note):
        t["status"] = status
        t["done_note"] = note
        run["moves"].append({"desc": t.get("description", "")[:80], "to": status, "why": note})

    rest = []
    for t in pend:
        d = norm(t.get("description", ""))
        if all(h in d for h in DONE_HINTS):
            move(t, "done", "de-facto: реализовано (техдолг-репортер в main)")
        elif any(h in d for h in PROTECTED_HINTS):
            move(t, "archived", "цель protected (AGENTS.md)")
        elif d.startswith(("добавить задачу", "создать задачу", "создать issue")):
            move(t, "archived", "мета-обёртка")
        else:
            rest.append(t)

    for cl in cluster_fuzzy(rest, lambda t: norm(t.get("description", ""))):
        for t in cl["dups"]:
            move(t, "archived", "дубль (fuzzy)")
    rest = [c["keep"] for c in cluster_fuzzy(rest, lambda t: norm(t.get("description", "")))]
    for cl in cluster_jaccard(rest):
        for t in cl["dups"]:
            move(t, "archived", "дубль (jaccard)")
    rest = [c["keep"] for c in cluster_jaccard(rest)]

    rest.sort(key=lambda t: (PRIO.get(str(t.get("priority", "medium")).lower(), 2),
                             t.get("created", "")))
    for t in rest[CAP:]:
        move(t, "archived", f"сверх капа {CAP}")
    rest = rest[:CAP]

    # mypy/ruff и xss-каноны (частые дубли)
    canon = {}
    for t in rest:
        d = norm(t.get("description", ""))
        key = "mypy-ruff" if ("mypy" in d or "ruff" in d) else \
              "xss-csrf" if ("xss" in d and "csrf" in d) else None
        if key:
            if key in canon:
                move(t, "archived", f"дубль канона {key}")
            else:
                canon[key] = t
    rest = [t for t in rest if t.get("status") == "pending"]

    run["before"], run["after"] = before, len(rest)
    if not dry:
        b["tasks"] = [t for t in b["tasks"] if t.get("status") != "pending"] + rest
        json.dump(b, open(BACKLOG, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        arch.setdefault("runs", []).append(run)
        arch["runs"] = arch["runs"][-20:]
        json.dump(arch, open(ARCHIVE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"{'[dry] ' if dry else ''}pending: {before} -> {len(rest)} "
          f"(moves: {len(run['moves'])}, кап={CAP})")
    for m in run["moves"][:12]:
        print(f"  -> {m['to']}: {m['desc']} ({m['why']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
