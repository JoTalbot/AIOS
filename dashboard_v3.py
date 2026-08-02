#!/usr/bin/env python3
"""
AIOS Dashboard v3 — сводка всех аккаунтов (web, nicegui).
Порт 8090, только localhost. Показывает: подписчики IG/TikTok, OLX, посылки,
почта, напоминания, шаблоны, подписки на цены.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from nicegui import ui

ROOT = Path(__file__).resolve().parent


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _analytics() -> dict:
    return _read_json(ROOT / "data" / "analytics_state.json")


def _reminders() -> list:
    try:
        return json.loads((ROOT / "data" / "reminders.json").read_text(encoding="utf-8"))
    except Exception:
        return []


def _np_parcels() -> dict:
    return _read_json(ROOT / "data" / "np_alerts_state.json")


def _price_subs() -> dict:
    return _read_json(ROOT / "data" / "olx_price_subs.json")


def _templates() -> dict:
    return _read_json(ROOT / "data" / "templates.json")


def _olx_stats() -> dict:
    try:
        conn = sqlite3.connect(str(ROOT / "data" / "olx_http.sqlite"))
        total = conn.execute("SELECT COUNT(*) FROM ads WHERE active = 1").fetchone()[0]
        min_p = conn.execute("SELECT MIN(price_value) FROM ads WHERE price_value > 0 AND active = 1").fetchone()[0]
        conn.close()
        return {"total": total, "min_price": min_p}
    except Exception:
        return {"total": 0, "min_price": None}


def build() -> None:
    ui.page_title("AIOS Dashboard")
    with ui.header().classes("bg-blue-900"):
        ui.label("AIOS — сводка аккаунтов").classes("text-2xl font-bold")
        ui.label(datetime.now().strftime("%d.%m.%Y %H:%M")).classes("text-sm")

    # Аналитика (подписчики)
    hist = _analytics()
    with ui.card().classes("w-full"):
        ui.label("📊 Аналитика").classes("text-lg font-bold")
        if hist:
            last_date = sorted(hist.keys())[-1]
            last = hist[last_date]
            with ui.row():
                ui.label(f"Instagram подписчики: {last.get('instagram_followers', '—')}").classes("text-base")
                ui.label(f"TikTok подписчики: {last.get('tiktok_followers', '—')}").classes("text-base")
                ui.label(f"TikTok лайки: {last.get('tiktok_likes', '—')}").classes("text-base")
        else:
            ui.label("Нет данных (снапшоты собираются ежедневно)")

    # OLX
    olx = _olx_stats()
    with ui.card().classes("w-full"):
        ui.label("🛒 OLX").classes("text-lg font-bold")
        ui.label(f"Активных объявлений в БД: {olx['total']} · мин цена: {olx['min_price'] or '—'} грн")
        subs = _price_subs()
        if subs:
            ui.label("Подписки на цены:").classes("text-sm font-bold")
            for chat, entries in subs.items():
                for e in entries:
                    ui.label(f"• {e.get('query')} — мин {e.get('last_min') or '?'} грн").classes("text-sm")

    # Посылки Новой Пошты
    parcels = _np_parcels()
    with ui.card().classes("w-full"):
        ui.label("📦 Новая Пошта — посылки").classes("text-lg font-bold")
        if parcels:
            for ttn, info in parcels.items():
                ui.label(f"• {ttn}: {info.get('status', '—')}").classes("text-sm")
        else:
            ui.label("Нет посылок в отслеживании")

    # Напоминания
    rem = _reminders()
    with ui.card().classes("w-full"):
        ui.label("⏰ Напоминания").classes("text-lg font-bold")
        if rem:
            for r in rem[:10]:
                ui.label(f"• {r.get('at', '')[:16]}: {r.get('text', '')}").classes("text-sm")
        else:
            ui.label("Нет активных напоминаний")

    # Шаблоны
    tpl = _templates()
    with ui.card().classes("w-full"):
        ui.label("📝 Шаблоны ответов").classes("text-lg font-bold")
        if tpl:
            for k, v in list(tpl.items())[:10]:
                ui.label(f"• <b>{k}</b>: {v[:60]}").classes("text-sm").props("contenteditable=false")
        else:
            ui.label("Шаблонов пока нет")

    ui.run(host="127.0.0.1", port=8090, reload=False, show=False)


if __name__ == "__main__":
    build()
