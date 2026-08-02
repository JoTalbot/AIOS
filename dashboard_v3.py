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


def _inventory() -> list:
    try:
        return json.loads((ROOT / "data" / "inventory.json").read_text(encoding="utf-8"))
    except Exception:
        return []


def _finance() -> list:
    try:
        return json.loads((ROOT / "data" / "finance.json").read_text(encoding="utf-8"))
    except Exception:
        return []


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

    # Склад
    inv = _inventory()
    with ui.card().classes("w-full"):
        ui.label("📦 Склад").classes("text-lg font-bold")
        if inv:
            total_qty = sum(x.get("qty", 0) for x in inv)
            total_val = sum(x.get("qty", 0) * x.get("price", 0) for x in inv)
            ui.label(f"Деталей: {len(inv)} · всего шт: {total_qty} · запасы: {total_val} грн").classes("text-sm")
            for x in inv[:12]:
                mark = "✅" if x.get("qty", 0) > 0 else "❌"
                ui.label(f"{mark} {x.get('name', '')} — {x.get('qty', 0)} шт · {x.get('price', 0)} грн").classes("text-sm")
        else:
            ui.label("Склад пуст")

    # Финансы
    fin = _finance()
    with ui.card().classes("w-full"):
        ui.label("💰 Финансы").classes("text-lg font-bold")
        if fin:
            sales = sum(x["amount"] for x in fin if x.get("kind") == "sale")
            exp = sum(x["amount"] for x in fin if x.get("kind") == "expense")
            ui.label(f"Продажи: {sales} · Расходы: {exp} · Прибыль: {sales - exp} грн").classes("text-sm")
            for x in fin[-6:][::-1]:
                em = "🟢" if x.get("kind") == "sale" else "🔴"
                ui.label(f"{em} {x.get('date', '')[:16]} — {x.get('desc', '')} — {x.get('amount')} грн").classes("text-sm")
        else:
            ui.label("Нет операций")

    ui.run(host="127.0.0.1", port=8090, reload=False, show=False)


if __name__ == "__main__":
    build()
