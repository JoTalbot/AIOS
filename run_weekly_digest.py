#!/usr/bin/env python3
"""
Недельный дайджест (вс 19:00 Киев): тренды ниш ВАЗ/ГАЗель за 7 дней,
топ выкупных лотов недели и статистика черновиков (подтверждено/отменено).
"""
from __future__ import annotations

import html
import json
import re
import os
import sqlite3
import statistics
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "olx_http.sqlite"
SNAPS = ROOT / "data" / "market_snapshots.json"
QUEUE = ROOT / "data" / "android_gateway" / "phone_brain.db"


def _env(key: str) -> str:
    v = os.environ.get(key, "")
    if v:
        return v
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _tg(text: str) -> bool:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = {"chat_id": int(chat), "text": html.escape(text)[:3900], "parse_mode": "HTML"}
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            return True
    except Exception:
        return False


def build() -> str:
    lines = [f"📊 <b>Недельный дайджест</b> — {datetime.now().strftime('%d.%m.%Y')}"]

    # тренды ниш из снапшотов
    try:
        snaps = json.loads(SNAPS.read_text(encoding="utf-8"))
        dates = sorted(snaps.keys())
        week = [d for d in dates if d >= (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")]
        if len(week) >= 2:
            first, last = snaps[week[0]], snaps[week[-1]]
            lines.append("\n🚗 Тренды ниш (медианы за неделю):")
            for q, cur in sorted(last.items(), key=lambda kv: -kv[1]["n"])[:6]:
                old = (first.get(q) or {}).get("median")
                arrow = ""
                if old:
                    pct = int((cur["median"] - old) / old * 100)
                    arrow = f" {'+' if pct > 0 else ''}{pct}%"
                lines.append(f"• {q}: {cur['median']} грн{arrow}")
    except Exception:
        pass

    # топ лотов недели: новые за 7 дней, цена <= 50% текущей медианы ниши
    try:
        con = sqlite3.connect(DB)
        by = {}
        for q, p in con.execute("select query, price_value from ads where active=1 and price_value>0"):
            by.setdefault(q, []).append(float(p))
        med = {q: statistics.median(v) for q, v in by.items() if len(v) >= 5}
        since = (datetime.now() - timedelta(days=7)).isoformat()
        lots = []
        for q, price, title, url, fs in con.execute(
                "select query, price_value, title, url, first_seen from ads "
                "where active=1 and price_value>=20"):
            if q in med and float(price) <= med[q] * 0.5 and str(fs or "") >= since:
                lots.append((float(price) / med[q], price, med[q], q, title, url))
        STOP_RE = re.compile(r"(хлам|мебел|квартир|перевозк|услуг|аренд)", re.IGNORECASE)
        lots = [l for l in lots if not STOP_RE.search(l[4] or "")]
        lots.sort()
        if lots:
            lines.append("\n🔥 Топ выкупных лотов недели:")
            for ratio, price, m, q, title, url in lots[:5]:
                lines.append(f"• {price:.0f} грн (медиана {m:.0f}) — {title[:55]}")
    except Exception:
        pass

    # статистика черновиков за неделю
    try:
        con = sqlite3.connect(QUEUE)
        week_ts = (datetime.now() - timedelta(days=7)).timestamp() * 1000
        rows = con.execute(
            "select kind, status, count(*) from jobs where rowid>0 group by kind, status").fetchall()
        done = sum(c for k, s, c in rows if s == "done" and "draft" in k or s == "done" and "send" in k)
        canc = sum(c for k, s, c in rows if s == "cancelled")
        pend = sum(c for k, s, c in rows if s == "need_confirm")
        lines.append(f"\n✍️ Черновики за неделю: выполнено {done}, отменено {canc}, "
                     f"ждут подтверждения {pend}")
        if canc and done:
            lines.append("Стиль: чаще подтверждаете — держим текущий тон черновиков.")
    except Exception:
        pass

    # сводка уведомлений мессенджеров за неделю
    try:
        notes = json.loads((ROOT / "data" / "android_gateway" / "notifications.json").read_text(encoding="utf-8"))
        since = (datetime.now() - timedelta(days=7)).isoformat()
        per_app = {}
        contacts = {}
        for n in notes if isinstance(notes, list) else []:
            if str(n.get("collected_at") or "") >= since:
                app = str(n.get("app") or "?")
                per_app[app] = per_app.get(app, 0) + 1
                t = str(n.get("title") or "").strip()
                if t and app in ("iMe Messenger", "WhatsApp"):
                    contacts[t] = contacts.get(t, 0) + 1
        if per_app:
            lines.append("\n💬 Уведомления за неделю: " +
                         ", ".join(f"{k}: {v}" for k, v in sorted(per_app.items(), key=lambda kv: -kv[1])))
            top = sorted(contacts.items(), key=lambda kv: -kv[1])[:3]
            if top:
                lines.append("Чаще всего писали: " + ", ".join(f"{k} ({v})" for k, v in top))
    except Exception:
        pass

    # скорость реакции за неделю
    try:
        notes = json.loads((ROOT / "data" / "android_gateway" / "notifications.json").read_text(encoding="utf-8"))
        since = (datetime.now() - timedelta(days=7)).isoformat()
        incoming = sum(1 for n in notes if isinstance(n, dict)
                       and str(n.get("package") or "") in
                       ("com.iMe.android", "com.whatsapp", "ua.slando")
                       and str(n.get("collected_at") or "") >= since)
        drafts = confirmed = cancelled = 0
        evp = ROOT / "data" / "android_gateway" / "phone_brain_events.jsonl"
        if evp.exists():
            for ln in evp.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(ln)
                except Exception:
                    continue
                if str(e.get("at") or "") >= since and e.get("type") == "llm_draft_ready":
                    drafts += 1
        con = sqlite3.connect(QUEUE)
        for s, c in con.execute("select status, count(*) from jobs "
                                "where kind='skill.run' group by status"):
            if s == "done":
                confirmed += c
            elif s == "cancelled":
                cancelled += c
        if incoming:
            lines.append(f"\n⚡ Реакция за неделю: входящих {incoming}, "
                         f"черновиков {drafts} ({int(drafts / incoming * 100)}%), "
                         f"подтверждено {confirmed}, отменено {cancelled}")
    except Exception:
        pass

    return "\n".join(lines)


def main() -> int:
    import sys
    text = build()
    if "--print" in sys.argv:
        print(text)
        return 0
    sent = _tg(text)
    print(json.dumps({"status": "ok" if sent else "error", "sent": sent}, ensure_ascii=False))
    return 0 if sent else 1


if __name__ == "__main__":
    raise SystemExit(main())
