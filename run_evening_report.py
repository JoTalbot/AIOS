#!/usr/bin/env python3
"""
AIOS Evening Report — вечерний отчёт за день: продажи/расходы/прибыль,
изменения на складе, новые заявки. Шлёт в Telegram в 21:00 (Киев).
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _env(key: str) -> str:
    if key in ("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        from tg_bot.credentials import secret_from_env_or_credential
        value = secret_from_env_or_credential(
            "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
        )
        if value:
            return value
    if key in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID", "AIOS_AUTO_CODER_CHAT_ID"):
        from tg_bot.credentials import read_systemd_credential
        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
    import os
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


def _tg(token: str, chat_id: int, text: str) -> None:
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3900],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def _run_script(name: str, args: list, timeout: int = 30) -> dict:
    r = subprocess.run(["/opt/aios/.venv/bin/python", str(ROOT / name)] + args,
                       capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    out = (r.stdout or "").strip()
    start = out.find("{")
    try:
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": out[-200:]}
    except Exception:
        return {"status": "error", "error": out[-200:]}


def build_report() -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    lines = [f"🌙 <b>Вечерний отчёт</b> — {today}"]

    # финансы за день
    try:
        fin = _run_script("run_finance.py", ["report", "1"])
        if fin.get("status") == "ok":
            lines.append(f"\n💰 <b>Финансы за день:</b>\n"
                         f"🟢 Продажи: {fin.get('sales')} грн\n"
                         f"🔴 Расходы: {fin.get('expenses')} грн\n"
                         f"📊 Прибыль: <b>{fin.get('profit')}</b> грн")
    except Exception:
        pass

    # склад
    try:
        inv = _run_script("run_inventory.py", ["stats"])
        if inv.get("status") == "ok":
            lines.append(f"\n📦 <b>Склад:</b> {inv.get('items_count')} деталей, "
                         f"{inv.get('total_qty')} шт, запасы на {inv.get('total_value')} грн")
            if inv.get("out_of_stock"):
                lines.append(f"🚫 Закончились: {', '.join(inv['out_of_stock'][:4])}")
    except Exception:
        pass

    # напоминания на завтра
    try:
        rem = json.loads((ROOT / "data" / "reminders.json").read_text(encoding="utf-8"))
        tomorrow = datetime.now() + timedelta(days=1)
        tom_rem = [r for r in rem if r.get("at", "").startswith(tomorrow.strftime("%Y-%m-%d"))]
        if tom_rem:
            lines.append(f"\n⏰ <b>Завтра:</b>\n" + "\n".join(
                f"• {r.get('at', '')[11:16]} — {r.get('text', '')}" for r in tom_rem[:5]))
    except Exception:
        pass

    # телефон
    try:
        health = json.loads((ROOT / "data" / "android_gateway" / "health.json").read_text(encoding="utf-8"))
        battery = health.get("battery")
        connected = bool(health.get("connected"))
        if isinstance(battery, int):
            warn = " ⚠️ поставьте на зарядку!" if battery < 20 else ""
            lines.append(f"\n📱 <b>Телефон:</b> "
                         f"{'онлайн' if connected else 'ОФЛАЙН'} · батарея {battery}%{warn}")
    except Exception:
        pass

    return "\n".join(lines)


def build_monthly() -> str:
    """Месячный отчёт: финансы за 30 дней + топ деталей."""
    today = datetime.now().strftime("%d.%m.%Y")
    lines = [f"📊 <b>Месячный отчёт</b> — {today}"]

    fin = _run_script("run_finance.py", ["report", "30"])
    if fin.get("status") == "ok":
        lines.append(f"\n💰 <b>Финансы за 30 дней:</b>\n"
                     f"🟢 Продажи: {fin.get('sales')} грн\n"
                     f"🔴 Расходы: {fin.get('expenses')} грн\n"
                     f"📊 Прибыль: <b>{fin.get('profit')}</b> грн")

    # топ проданных деталей
    try:
        items = json.loads((ROOT / "data" / "finance.json").read_text(encoding="utf-8"))
        sales = [x for x in items if x.get("kind") == "sale"]
        if sales:
            by_name = {}
            for s in sales:
                d = s.get("desc", "")
                by_name.setdefault(d, 0)
                by_name[d] += s.get("amount", 0)
            top = sorted(by_name.items(), key=lambda kv: kv[1], reverse=True)[:5]
            if top:
                lines.append("\n🏆 <b>Топ продаж:</b>\n" + "\n".join(
                    f"• {_esc(d)} — {v} грн" for d, v in top))
    except Exception:
        pass

    inv = _run_script("run_inventory.py", ["stats"])
    if inv.get("status") == "ok":
        lines.append(f"\n📦 <b>Склад:</b> {inv.get('items_count')} деталей, запасы {inv.get('total_value')} грн")
    return "\n".join(lines)


def _esc(s) -> str:
    import html
    return html.escape(str(s or ""))


def main() -> int:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Нет токена/чата"); return 1
    if "--monthly" in sys.argv:
        report = build_monthly()
    else:
        report = build_report()
    try:
        _tg(token, int(chat), report)
        print("Вечерний отчёт отправлен")
        return 0
    except Exception as e:
        print("Ошибка:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
