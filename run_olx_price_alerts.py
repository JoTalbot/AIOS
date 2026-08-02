#!/usr/bin/env python3
"""
AIOS OLX Price Alerts — следит за ценами по подпискам («следи за ценой <запрос>»).
Раз в N минут (systemd) берёт из БД ads (собрана коллектором) минимальную цену
по запросу за последние 3 дня и уведомляет в Telegram при снижении.

Подписки хранятся в data/olx_price_subs.json:
  {"chat_id": [{"query": "...", "last_min": 5000, "since": "..."}]}
"""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

SUBS_FILE = ROOT / "data" / "olx_price_subs.json"
ADS_DB = ROOT / "data" / "olx_http.sqlite"


def _env(key: str) -> str:
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


def _load_subs() -> dict:
    try:
        return json.loads(SUBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_subs(subs: dict) -> None:
    SUBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUBS_FILE.write_text(json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8")


def _tg(token: str, chat_id: int, text: str) -> None:
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3800],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def _min_price(query: str, days: int = 3) -> float | None:
    """Минимальная цена по запросу за последние N дней (из свежих объявлений)."""
    try:
        conn = sqlite3.connect(ADS_DB)
        # берём записи за последние сутки по collection_runs (упрощённо: все свежие ads)
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT price_value FROM ads WHERE query LIKE ? AND price_value > 0 "
            "AND active = 1 AND collected_at >= ? ORDER BY collected_at DESC LIMIT 200",
            (f"%{query}%", since)).fetchall()
        conn.close()
    except Exception:
        return None
    prices = [r[0] for r in rows if isinstance(r[0], (int, float))]
    if not prices:
        return None
    return min(prices)


def check_alerts() -> int:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    subs = _load_subs()
    if not subs:
        print("Нет подписок на цены")
        return 0
    sent = 0
    now = datetime.now()
    for chat_s, entries in subs.items():
        chat_id = int(chat_s)
        for e in entries:
            q = e.get("query", "")
            last = e.get("last_min")
            cur = _min_price(q)
            if cur is None:
                continue
            if last is not None and cur < last * 0.95:  # снижение >5%
                if token:
                    try:
                        _tg(token, chat_id,
                            f"📉 <b>Цена снизилась на OLX!</b>\n"
                            f"«{q}»: {cur} грн (было {last} грн, -{int((1 - cur / last) * 100)}%)\n"
                            f"Проверить: поиск по «{q}»")
                        sent += 1
                        print(f"  → снижение {q}: {last} -> {cur}")
                    except Exception as ex:
                        print(f"  ! err: {ex}")
            e["last_min"] = cur
            e["since"] = now.strftime("%Y-%m-%d %H:%M")
        # сохраняем обновлённые значения
    _save_subs(subs)
    print(f"Проверено подписок: {sum(len(v) for v in subs.values())}, уведомлений: {sent}")
    return sent


if __name__ == "__main__":
    # режим --probe <query>: просто вывести минимальную цену
    if len(sys.argv) >= 3 and sys.argv[1] == "--probe":
        p = _min_price(sys.argv[2])
        print(p if p is not None else "")
        sys.exit(0)
    sys.exit(check_alerts())
