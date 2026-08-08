#!/usr/bin/env python3
"""AIOS v22 — ежедневный отчёт API-монетизации (cron 21:05).

Читает data/api_usage_ledger.jsonl, агрегирует выручку за 24ч по клиентам
и продуктам, печатает JSON и (с --telegram) шлёт TG-дайджест.
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

BASE = "/root/AIOS"
sys.path.insert(0, BASE)


def _data_dir() -> Path:
    for p in (os.environ.get("AIOS_DATA_DIR"),
              "/app/data" if os.path.exists("/app/data") else None,
              f"{BASE}/data"):
        if p and os.path.isdir(p):
            return Path(p)
    return Path(f"{BASE}/data")


def load_ledger(hours: float = 24.0):
    ledger = _data_dir() / "api_usage_ledger.jsonl"
    since = time.time() - hours * 3600
    events = []
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except Exception:
                continue
            if float(e.get("ts", 0)) >= since:
                events.append(e)
    return events


def build_report(hours: float = 24.0) -> dict:
    events = load_ledger(hours)
    by_client_usd = defaultdict(float)
    by_client_req = Counter()
    by_product_usd = defaultdict(float)
    for e in events:
        c = e.get("client", "?")
        by_client_usd[c] += float(e.get("cost_usd", 0))
        by_client_req[c] += 1
        by_product_usd[e.get("product", "generic")] += float(e.get("cost_usd", 0))
    total = round(sum(by_client_usd.values()), 4)
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "window_hours": hours,
        "events": len(events),
        "revenue_usd": total,
        "by_client": {c: {"requests": by_client_req[c], "revenue_usd": round(v, 4)}
                      for c, v in sorted(by_client_usd.items(), key=lambda kv: -kv[1])},
        "by_product_usd": {k: round(v, 4) for k, v in
                           sorted(by_product_usd.items(), key=lambda kv: -kv[1])},
    }


def tg_text(r: dict) -> str:
    lines = ["💰 <b>API Monetization — дневной отчёт</b>",
             f"Выручка за {r['window_hours']:g}ч: <b>${r['revenue_usd']:.2f}</b> ({r['events']} запросов)"]
    if r["by_client"]:
        lines.append("<b>По клиентам:</b>")
        for c, v in r["by_client"].items():
            lines.append(f"• {c}: {v['requests']} запр. (${v['revenue_usd']:.2f})")
    if r["by_product_usd"]:
        lines.append("<b>По продуктам:</b> " + ", ".join(
            f"{k} ${v:.2f}" for k, v in r["by_product_usd"].items()))
    if not r["events"]:
        lines.append("Запросов не было — датапродукт ждёт первых клиентов (Phase B: пилот).")
    lines.append("#апи #монетизация")
    return "\n".join(lines)


def main():
    tg = "--telegram" in sys.argv
    hours = 24.0
    for a in sys.argv:
        if a.startswith("--hours="):
            hours = float(a.split("=", 1)[1])
    r = build_report(hours)
    if tg:
        from run_freelance_funnel import send_tg
        ok = send_tg(tg_text(r))
        print(json.dumps({"telegram_sent": ok, **r}, ensure_ascii=False, indent=1))
    else:
        print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
