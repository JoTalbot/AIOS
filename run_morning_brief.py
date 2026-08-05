#!/usr/bin/env python3
"""
AIOS Morning Brief — утренний брифинг владельцу (07:30 Киев):
телефон (батарея/онлайн), необработанные черновики phone-brain, уведомления
мессенджеров/OLX за сутки, склад (нет в наличии), финансы за вчера, напоминания.
Только чтение локальных данных — ничего не трогает на устройствах.
"""
from __future__ import annotations

import html
import json
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _env(key: str) -> str:
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _tg(text: str) -> bool:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = {"chat_id": int(chat), "text": html.escape(text)[:3900],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60):
            return True
    except Exception:
        return False


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def build() -> str:
    now = datetime.now()
    lines = [f"☀️ <b>Утренний брифинг</b> — {now.strftime('%d.%m.%Y')}"]

    # телефон
    health = _read(ROOT / "data" / "android_gateway" / "health.json", {})
    if isinstance(health, dict) and health.get("battery") is not None:
        batt = health.get("battery")
        state = "онлайн" if health.get("connected") else "ОФЛАЙН"
        warn = " ⚠️ зарядите!" if (isinstance(batt, int) and batt < 20) else ""
        lines.append(f"📱 Телефон: {state}, батарея {batt}%{warn}")

    # черновики, ждущие подтверждения
    try:
        import sqlite3
        con = sqlite3.connect(ROOT / "data" / "android_gateway" / "phone_brain.db")
        pending = con.execute(
            "select count(*) from jobs where status in ('need_confirm','queued')").fetchone()[0]
        if pending:
            lines.append(f"✍️ Ждут вашего подтверждения в TG: {pending} задач(и) — "
                         f"скажите «подтверди N» или отмените")
    except Exception:
        pass

    # уведомления за сутки по источникам
    notes = _read(ROOT / "data" / "android_gateway" / "notifications.json", [])
    day_ago = (now - timedelta(hours=24)).isoformat()
    per_app = {}
    for n in notes if isinstance(notes, list) else []:
        if str(n.get("collected_at") or "") >= day_ago:
            per_app[n.get("app") or "?"] = per_app.get(n.get("app") or "?", 0) + 1
    if per_app:
        parts = ", ".join(f"{k}: {v}" for k, v in sorted(per_app.items(), key=lambda kv: -kv[1]))
        lines.append(f"🔔 Уведомлений за сутки — {parts}")

    # склад
    inv = _read(ROOT / "data" / "inventory.json", [])
    if isinstance(inv, list):
        oos = [i.get("name") for i in inv if (i.get("qty") or 0) <= 0]
        avail = [i for i in inv if (i.get("qty") or 0) > 0]
        if avail:
            lines.append("📦 В наличии: " + ", ".join(
                f"{i.get('name')} ({int(i.get('price') or 0)} грн)" for i in avail[:4]))
        if oos:
            lines.append("🚫 Закончились: " + ", ".join(oos[:4]))

    # финансы за вчера
    fin = _read(ROOT / "data" / "finance.json", [])
    if isinstance(fin, list):
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        ops = [x for x in fin if str(x.get("date") or "").startswith(yesterday)]
        sales = sum(x.get("amount") or 0 for x in ops if x.get("kind") == "sale")
        exp = sum(x.get("amount") or 0 for x in ops if x.get("kind") == "expense")
        if ops:
            lines.append(f"💰 Вчера: продажи {sales} грн, расходы {exp} грн")
        else:
            lines.append("💰 Вчера операций не было")

    # напоминания на сегодня
    rem = _read(ROOT / "data" / "reminders.json", [])
    today = now.strftime("%Y-%m-%d")
    todays = [r for r in rem if isinstance(r, dict) and str(r.get("at") or "").startswith(today)]
    if todays:
        lines.append("⏰ Сегодня: " + "; ".join(
            f"{str(r.get('at'))[11:16]} {r.get('text')}" for r in todays[:4]))

    return "\n".join(lines)


def main() -> int:
    text = build()
    sent = _tg(text)
    print(json.dumps({"status": "ok" if sent else "error", "sent": sent}, ensure_ascii=False))
    return 0 if sent else 1


if __name__ == "__main__":
    raise SystemExit(main())
