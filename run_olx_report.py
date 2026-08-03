#!/usr/bin/env python3
"""
AIOS OLX Report — сводка по OLX: активные объявления, чат, публикации.

  python run_olx_report.py   # печать сводки (и в Telegram, если токен задан)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

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


def _load_journal() -> list:
    try:
        return json.loads((ROOT / "data" / "olx_published.json").read_text(encoding="utf-8"))
    except Exception:
        return []


def build_report() -> dict:
    from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter
    import asyncio

    async def _fetch():
        a = OLXChromeTwinAdapter(config={"olx_login": "959052288"})
        try:
            ads = await a.list_my_ads(20)
            chat = await a.chat_list(20)
            return ads, chat
        finally:
            await a.close()

    try:
        ads, chat = asyncio.run(_fetch())
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}

    journal = _load_journal()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    published_today = [j for j in journal if (j.get("ts") or "").startswith(today)]

    total_price = 0
    for a in ads:
        try:
            total_price += int(str(a.get("price") or "0").replace(" ", ""))
        except Exception:
            pass

    chat_unread = 0
    if chat.get("status") == "ok":
        chat_unread = 1 if chat.get("unread_present") else 0

    return {
        "status": "ok",
        "ads_count": len(ads),
        "ads": [{"id": a.get("id"), "title": a.get("title"), "price": a.get("price")} for a in ads],
        "total_price": total_price,
        "chat_unread": chat_unread,
        "chat_error": chat.get("error") if chat.get("status") != "ok" else "",
        "published_today": len(published_today),
    }


def format_report(r: dict) -> str:
    lines = ["🛒 <b>Отчёт по OLX</b>"]
    if r.get("status") != "ok":
        lines.append(f"❌ {r.get('error', '?')}")
        return "\n".join(lines)
    lines.append(f"Активных объявлений: <b>{r.get('ads_count')}</b>")
    lines.append(f"Сумма цен: <b>{r.get('total_price')} грн</b>")
    lines.append(f"Опубликовано сегодня: {r.get('published_today')}")
    un = r.get("chat_unread", 0)
    lines.append(f"Непрочитанных в чате: {'🔴 ' + str(un) if un else '0'}")
    if r.get("chat_error"):
        lines.append(f"⚠️ Чат: {r['chat_error'][:60]}")
    if r.get("ads"):
        lines.append("")
        for a in r["ads"][:10]:
            lines.append(f"• {a.get('id')} — {a.get('title')}: {a.get('price')} грн")
    return "\n".join(lines)


def main() -> None:
    r = build_report()
    text = format_report(r)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    if token and r.get("status") == "ok":
        try:
            _tg(token, text)
        except Exception as e:
            print(f"[olx-report] tg error: {e}")


if __name__ == "__main__":
    main()
