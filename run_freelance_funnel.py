#!/usr/bin/env python3
"""
AIOS Freelance Funnel v20.0 — трекинг конверсии ставок в победы.
Считает воронку scanned → evaluated → BID_SUBMITTED → WON/LOST,
даёт разрез по источникам и нишам, шлёт отчёт в Telegram.

Usage:
  python run_freelance_funnel.py              # JSON отчёт
  python run_freelance_funnel.py --telegram   # отправить сводку в TG
  python run_freelance_funnel.py --mark WON task_id task_id ...  # пометить исход
"""
import json
import sys
import time
import urllib.request
from pathlib import Path
from collections import Counter, defaultdict

DATA = Path("/root/AIOS/data/freelance_tasks.json")
STATE = Path("/root/AIOS/data/freelance_funnel_state.json")

WIN_STATUSES = {"WON", "PAID", "COMPLETED"}
LOST_STATUSES = {"LOST", "REJECTED", "EXPIRED", "CANCELLED"}


def load_tasks():
    if DATA.exists():
        return json.loads(DATA.read_text(encoding="utf-8"))
    return []


def _env(name):
    import os
    v = os.getenv(name)
    if v:
        return v
    ef = Path("/root/AIOS/.env")
    if ef.exists():
        for line in ef.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def send_tg(text):
    token, chat = _env("TELEGRAM_BOT_TOKEN"), _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = {"chat_id": int(chat), "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        print(f"TG error: {e}", file=sys.stderr)
        return False


def build_report():
    tasks = load_tasks()
    by_status = Counter(t.get("status", "?") for t in tasks)
    by_source = defaultdict(lambda: Counter())
    budget_by_source = defaultdict(float)
    for t in tasks:
        src = t.get("source", "?")
        st = t.get("status", "?")
        by_source[src][st] += 1
        if st == "BID_SUBMITTED" or st in WIN_STATUSES:
            budget_by_source[src] += float(t.get("budget_usd") or 0)

    open_bids = sum(v for s, v in by_status.items() if s == "BID_SUBMITTED")
    won = sum(by_status.get(s, 0) for s in WIN_STATUSES)
    lost = sum(by_status.get(s, 0) for s in LOST_STATUSES)
    decided = won + lost
    win_rate = round(100 * won / decided, 1) if decided else None
    pipeline_usd = sum(float(t.get("budget_usd") or 0) for t in tasks if t.get("status") == "BID_SUBMITTED")

    # новые ставки за последние 7 дней
    week_ago = time.time() - 7 * 86400
    new_week = sum(1 for t in tasks if t.get("created_at", 0) > week_ago)

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_tasks": len(tasks),
        "new_last_7d": new_week,
        "status_funnel": dict(by_status),
        "open_bids": open_bids,
        "won": won,
        "lost": lost,
        "win_rate_pct": win_rate,
        "pipeline_open_usd": round(pipeline_usd, 2),
        "by_source": {s: dict(c) for s, c in sorted(by_source.items())},
        "by_niche": dict(Counter(t.get("category", "?") for t in tasks)),
        "budget_by_source_usd": {s: round(v, 2) for s, v in sorted(budget_by_source.items())},
    }
    STATE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def tg_text(r):
    lines = [
        "📊 <b>Freelance Funnel</b>",
        f"Всего задач: <b>{r['total_tasks']}</b> (+{r['new_last_7d']} за 7д)",
        f"Открытых ставок: <b>{r['open_bids']}</b> на <b>${r['pipeline_open_usd']:.0f}</b>",
    ]
    if r["win_rate_pct"] is not None:
        lines.append(f"Win-rate: <b>{r['win_rate_pct']}%</b> ({r['won']}W/{r['lost']}L)")
    else:
        lines.append("Побед пока нет — воронка на этапе накопления ставок")
    if r.get("by_niche"):
        top = sorted(r["by_niche"].items(), key=lambda kv: -kv[1])[:4]
        lines.append("<b>Ниши:</b> " + ", ".join(f"{k}×{v}" for k, v in top))
    lines.append("<b>По источникам:</b>")
    for src, sts in r["by_source"].items():
        bud = r["budget_by_source_usd"].get(src, 0)
        lines.append(f"• {src}: {sum(sts.values())} задач (${bud:.0f})")
    lines.append("#фриланс #воронка")
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--mark":
        outcome, ids = args[1], args[2:]
        tasks = load_tasks()
        marked = 0
        for t in tasks:
            if t.get("id") in ids:
                t["status"] = outcome
                t["outcome_at"] = time.time()
                marked += 1
        DATA.write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"marked": marked, "outcome": outcome}, ensure_ascii=False))
        return

    r = build_report()
    if "--telegram" in args:
        ok = send_tg(tg_text(r))
        print(json.dumps({"telegram_sent": ok, "report_file": str(STATE)}, ensure_ascii=False))
    else:
        print(json.dumps(r, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
