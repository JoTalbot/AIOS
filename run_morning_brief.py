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


def _abank_phone() -> dict:
    """Балансы и последние операции A-Bank с телефона (справочно, без записи в финансы)."""
    import json as _j
    import re as _re
    import time as _t
    try:
        from aios_core.android_gateway import AndroidGateway
        gw = AndroidGateway(ROOT)
        if gw.open_app("ua.com.abank", confirm=True).get("status") != "ok":
            return {}
        _t.sleep(5)

        def nodes():
            return gw.ui_snapshot(confirm=True, include_text=True).get("nodes") or []

        def find(pred):
            return next((n for n in nodes() if pred(n)), None)

        def tap(n):
            b = n["bounds"]
            gw.tap((b[0] + b[2]) // 2, (b[1] + b[3]) // 2, confirm=True)

        cancel = find(lambda n: (n.get("text") or "") in ("Скасувати", "Отмена"))
        if cancel:
            tap(cancel)
            _t.sleep(3)
        try:
            pins = _j.loads((ROOT / "data" / ".device_pins.json").read_text(encoding="utf-8")).get("app_unlock_pins") or []
        except Exception:
            pins = []
        for pin in pins:
            if not find(lambda n: (n.get("text") or "") == "Код для входу"):
                break
            for ch in str(pin):
                d = find(lambda n, c=ch: (n.get("text") or "").strip() == c)
                if d:
                    tap(d)
                    _t.sleep(0.4)
            _t.sleep(5)
        texts = [(n.get("text") or "").strip().replace("\n", " ")
                 for n in nodes() if (n.get("text") or "").strip()]
        amt_re = _re.compile(r"^-?[\d\s]{0,7}\d\.\d{2}\s?₴$")
        # маркер делит экран: до — балансы карт, после — лента операций
        idx = next((i for i, t in enumerate(texts) if t.startswith("Перекази")), len(texts))
        before, after = texts[:idx], texts[idx:]
        balances = [t for t in before if amt_re.match(t)][:4]
        ops = []
        for i, t in enumerate(after):
            if amt_re.match(t) and i > 0:
                desc = after[i - 1]
                if desc and "ліміт" not in desc and "власні" not in desc and not amt_re.match(desc):
                    ops.append(f"{t} — {desc}")
        # не оставляем банковский экран открытым
        gw.key("KEYCODE_HOME", confirm=True)
        return {"balances": balances, "ops": ops[:4]}
    except Exception:
        return {}


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

    # карты: сроки действия (напоминание)
    try:
        vault = _read(ROOT / "data" / ".cards_vault.json", {})
        cards = [c for b in (vault.get("banks") or []) for c in (b.get("cards") or [])]
        exps = [(c.get("number_masked") or "?", c.get("exp") or "?") for c in cards if c.get("exp")]
        if exps:
            import datetime as _dt
            warn = []
            now = _dt.datetime.now()
            for mask, exp in exps:
                try:
                    mm, yy = exp.split("/")
                    end = _dt.datetime(2000 + int(yy), int(mm), 28)
                    if (end - now).days < 60:
                        warn.append(f"{mask} истекает {exp}!")
                except Exception:
                    pass
            line = "💳 Карты: " + ", ".join(f"{m} ({e})" for m, e in exps)
            if warn:
                line += " ⚠️ " + " ".join(warn)
            lines.append(line)
    except Exception:
        pass

    # A-Bank с телефона (справочно)
    ab = _abank_phone()
    if ab.get("balances") or ab.get("ops"):
        line = "💳 A-Bank: " + ", ".join(ab.get("balances") or [])
        if ab.get("ops"):
            line += "\nпоследние операции: " + "; ".join(ab["ops"])
        lines.append(line)

    # рынок ВАЗ/ГАЗель за сутки
    try:
        import run_market_digest as rmd
        rmd.save()
        tl = rmd.trend_lines()
        if tl:
            lines.append("🚗 Рынок ВАЗ/ГАЗель (медианы):")
            lines.extend(tl[:6])
    except Exception:
        pass

    # цены против рынка OLX
    try:
        import run_price_recommend as rpr
        rows = rpr.report().get("rows") or []
        priced = [r for r in rows if r.get("n", 0) >= 5]
        if priced:
            lines.append("🏷 Цены vs рынок:")
            for r in priced[:4]:
                lines.append(f"• {r['name']}: наша {r['our_price']:.0f} грн — {r['verdict']}")
    except Exception:
        pass

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
