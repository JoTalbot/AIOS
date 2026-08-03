#!/usr/bin/env python3
"""
AIOS OLX Chat Alerts — уведомления в Telegram о новых сообщениях покупателей
в чате OLX (/uk/myaccount/answers).

  python run_olx_chat_alerts.py --init   # база (не уведомлять)
  python run_olx_chat_alerts.py --check  # один проход
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE_FILE = ROOT / "data" / "olx_chat_alerts_state.json"
CHAT_ID = 588113957


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


def _hash(name: str, text: str) -> str:
    return hashlib.md5(f"{name}|{text[:100]}".encode()).hexdigest()[:16]


def run_check(init: bool = False) -> dict:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    if not token:
        return {"status": "error", "error": "нет TELEGRAM_BOT_TOKEN"}
    state = _load_state()
    if not state.get("enabled", True) and not init:
        return {"status": "disabled"}

    from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter
    import asyncio

    async def _fetch():
        a = OLXChromeTwinAdapter(config={"olx_login": "959052288"})
        try:
            return await a.chat_list(20)
        finally:
            await a.close()

    try:
        r = asyncio.run(_fetch())
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    if r.get("status") != "ok":
        return r

    threads = r.get("threads") or []
    seen = state.setdefault("seen", {})
    new_notify = []
    for t in threads:
        name = t.get("name", "?")
        text = t.get("text", "")
        h = _hash(name, text)
        if seen.get(name) == h:
            continue
        seen[name] = h
        if not init:
            new_notify.append(t)

    notified = 0
    if not init:
        for t in new_notify:
            txt = (f"💬 <b>Новое сообщение на OLX</b> от {t.get('name')}\n"
                   f"{t.get('text', '')[:300]}\n\n"
                   f"Ответить: «ответь покупателю на олх: {t.get('name')}: текст»")
            try:
                _tg(token, txt)
                notified += 1
            except Exception as e:
                print(f"[olx-chat-alerts] tg error: {e}")
    state["notified"] = state.get("notified", 0) + notified
    state["last_check"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save_state(state)
    return {"status": "ok", "new": len(new_notify), "notified": notified if not init else 0,
            "unread": r.get("unread_present", False)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--on", action="store_true")
    ap.add_argument("--off", action="store_true")
    args = ap.parse_args()
    if args.on or args.off:
        st = _load_state()
        st["enabled"] = bool(args.on)
        _save_state(st)
        print(json.dumps({"status": "ok", "enabled": st["enabled"]}))
        return
    r = run_check(init=args.init or False)
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
