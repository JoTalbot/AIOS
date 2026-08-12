#!/usr/bin/env python3
"""
Сканер выгодных лотов на выкуп (ВАЗ/ГАЗель/авторазборки).
Новое активное объявление с ценой <= 50% медианы своей ниши → TG-алерт.
Дедуп по id объявления, не более 3 алертов за прогон. Таймер 30 минут.
"""
from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import statistics
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "olx_http.sqlite"
STATE = ROOT / "data" / "deal_scanner_state.json"


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


DONOR_RE = re.compile(
    r"(розбор|разбор|rozbork|донор|по запчасти|під розбор|на розбор|целиком|цевий|"
    r"продам (авто|машину|ваз|газель)|куплю авто|на запчастини|на запчасти)",
    re.IGNORECASE)
VAZGAZ_RE = re.compile(r"(ваз|vaz|лада|lada|газел|gazel|газ )", re.IGNORECASE)


def run(dry: bool = False) -> dict:
    con = sqlite3.connect(DB)
    by: dict[str, list[float]] = {}
    for q, p in con.execute("select query, price_value from ads where active=1 and price_value>0"):
        by.setdefault(q, []).append(float(p))
    medians = {q: statistics.median(v) for q, v in by.items() if len(v) >= 5}
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    seen = set(state.get("seen") or [])
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    deals = []
    for ad_id, q, title, price, url, first_seen in con.execute(
            "select id, query, title, price_value, url, first_seen from ads "
            "where active=1 and price_value>0"):
        if ad_id in seen or q not in medians:
            continue
        seen.add(ad_id)
        med = medians[q]
        if float(price) <= med * 0.5 and float(price) >= 20 and str(first_seen or "") >= since:
            deals.append({"id": ad_id, "query": q, "title": title,
                          "price": float(price), "median": med, "url": url})
    state["seen"] = list(seen)[-5000:]
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("day") != today:
        state["day"] = today
        state["sent_today"] = 0
    quota = max(0, 3 - int(state.get("sent_today") or 0))
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    donors = [d for d in deals if DONOR_RE.search(d["title"] or "") and VAZGAZ_RE.search(d["title"] or "")]
    parts = [d for d in deals if d not in donors]
    sent = 0
    for d in (donors[:quota] or parts[:quota]):
        kind = "🚙 <b>ДОНОР под разбор</b>" if d in donors else "🔥 <b>Выгодный лот</b>"
        msg = (f"{kind} [{d['query']}]: {d['price']:.0f} грн "
               f"(медиана {d['median']:.0f})\n{d['title'][:80]}\n{d['url']}")
        if dry:
            print("DRY:", msg.replace("\n", " | ")[:160])
        elif _tg(msg):
            sent += 1
    if sent:
        try:
            st = json.loads(STATE.read_text(encoding="utf-8"))
            st["sent_today"] = int(st.get("sent_today") or 0) + sent
            STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return {"status": "ok", "found": len(deals), "sent": sent}


def main() -> int:
    import sys
    print(json.dumps(run(dry="--dry" in sys.argv), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
