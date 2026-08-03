#!/usr/bin/env python3
"""
AIOS SMS Alerts — уведомления о новых SMS телефона (+380959052288)
в Telegram через Google Messages for Web (Messages-адаптер).

  python run_sms_alerts.py --init    # взять текущие SMS за базу (не уведомлять)
  python run_sms_alerts.py --check   # один проход: уведомить о новых важных SMS
  python run_sms_alerts.py --once    # то же, что --check

Что считается «важным» (по умолчанию):
- любое SMS с 4-8-значным кодом подтверждения;
- отправитель из IMPORTANT_SENDERS (OLX, Новая Почта, Stocar, банки и т.п.);
- текст содержит ключевые слова (код, посылка, ТТН, отправлено, доставлено и т.п.).
Остальные SMS (промо и т.п.) просто запоминаются, без уведомлений.

Управление: data/sms_alerts_state.json (вкл/выкл, seen-слепки, статистика).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE_FILE = ROOT / "data" / "sms_alerts_state.json"
CHAT_ID = 588113957

IMPORTANT_SENDERS = (
    "olx", "олх", "nova", "нова", "пошт", "poshta", "stocar", "банк",
    "приват", "monobank", "київстар", "kyivstar", "lifecell", "viber",
    "telegram", "google", "apple", "укрзалізниця", "ukrzaliznytsia", "rozetka",
)
KEYWORDS = (
    "код", "code", "verif", "підтвердж", "подтвержд", "посилк", "посылк",
    "відправлено", "отправлено", "доставлено", "доставк", "ттн", "ttn",
    "замовлення", "заказ", "оплат", "oplat", "рахунок", "відновлення",
)
CODE_RE = re.compile(r"\b(\d{4,8})\b")


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


def _tg(token: str, text: str) -> None:
    payload = {"chat_id": CHAT_ID, "text": text[:3900], "parse_mode": "HTML",
               "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"enabled": True, "seen": {}, "notified": 0}


def _save_state(st: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_important(sender: str, text: str) -> tuple[bool, str]:
    s = (sender or "").lower()
    t = (text or "").lower()
    if CODE_RE.search(text or ""):
        return True, "код"
    for k in IMPORTANT_SENDERS:
        if k in s:
            return True, "отправитель"
    for k in KEYWORDS:
        if k in t:
            return True, "ключевое слово"
    return False, ""


def _hash(sender: str, preview: str) -> str:
    return hashlib.md5(f"{sender}|{preview[:80]}".encode()).hexdigest()[:16]


def run_check(init: bool = False, all_msgs: bool = False) -> dict:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    if not token:
        return {"status": "error", "error": "нет TELEGRAM_BOT_TOKEN"}
    state = _load_state()
    if not state.get("enabled", True) and not init:
        return {"status": "disabled"}

    from aios_core.platforms.messages_web_chrome_twin_adapter import MessagesWebChromeTwinAdapter
    import asyncio

    async def _fetch():
        a = MessagesWebChromeTwinAdapter()
        try:
            r = await a.latest_sms(30)
            return r.get("sms", [])
        finally:
            await a.close()

    try:
        sms = asyncio.run(_fetch())
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}

    seen = state.setdefault("seen", {})
    new_important = []
    new_skipped = 0
    for s in sms:
        sender = s.get("sender", "?")
        preview = s.get("text", "")
        h = _hash(sender, preview)
        if seen.get(sender) == h:
            continue
        seen[sender] = h
        important, why = _is_important(sender, preview)
        if not important and not all_msgs:
            new_skipped += 1
            continue
        new_important.append({"sender": sender, "text": preview, "code": s.get("code", ""), "why": why})

    notified = 0
    if not init:
        for it in new_important:
            code = it.get("code") or ""
            code_txt = f"\n🔑 Код: <b>{code}</b>" if code else ""
            txt = (f"📩 <b>SMS: {it['sender']}</b>{code_txt}\n"
                   f"{it['text'][:350]}")
            try:
                _tg(token, txt)
                notified += 1
            except Exception as e:
                print(f"[sms-alerts] tg error: {e}")
    state["notified"] = state.get("notified", 0) + notified
    state["last_check"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save_state(state)
    return {"status": "ok", "new": len(new_important), "notified": notified if not init else 0,
            "skipped": new_skipped, "enabled": state.get("enabled", True)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--on", action="store_true")
    ap.add_argument("--off", action="store_true")
    args = ap.parse_args()

    if args.on or args.off:
        st = _load_state()
        st["enabled"] = bool(args.on)
        _save_state(st)
        print(json.dumps({"status": "ok", "enabled": st["enabled"]}))
        return

    r = run_check(init=args.init or False, all_msgs=args.all or False)
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
