"""Живая сводка AIOS — единый стиль форматирования для Telegram-бота.

Собирает актуальные показатели по всем направлениям (склад, OLX, конкуренты,
фриланс, система) и форматирует их в едином стиле: секции, иконки, аккуратные отступы.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

_TRIGGERS = (
    "сводка", "дашборд", "итоги", "обзор", "все показатели", "статус системы",
    "📊 сводка", "общая сводка", "что по деньгам", "что по бизнесу",
)

# Триггеры фриланс-сводки (кнопка «💼 Фриланс»)
_FREELANCE_TRIGGERS = (
    "фриланс", "ставки фриланса", "заказы фриланса", "💼 фриланс",
    "сколько заявок", "что по фрилансу",
)


def _load(name: str, default):
    p = DATA / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt(n) -> str:
    try:
        return f"{float(n):,.0f}".replace(",", " ")
    except Exception:
        return str(n)


def warehouse_block() -> str:
    items = _load("inventory.json", [])
    if not items:
        return "📦 Склад: нет данных"
    total_qty = sum(int(it.get("qty", 0)) for it in items)
    total_val = sum(float(it.get("price", 0)) * int(it.get("qty", 0)) for it in items)
    pub = _load("olx_published.json", [])
    lines = [
        "🏬 <b>Склад</b>",
        f"  📦 {len(items)} позиций · {total_qty} ед.",
        f"  💰 Стоимость: <b>{_fmt(total_val)} грн</b>",
        f"  🛒 На OLX: {len(pub) if isinstance(pub, list) else '?'}",
    ]
    return "\n".join(lines)


def competitors_block() -> str:
    mon = _load("competitor_monitor.json", {})
    if not mon or not mon.get("items"):
        return "🆚 Конкуренты: нет данных (запусти мониторинг)"
    below = sum(1 for i in mon["items"] if i["position"] == "below_market")
    above = sum(1 for i in mon["items"] if i["position"] == "above_market")
    no_comp = sum(1 for i in mon["items"] if i["competitors"] == 0)
    with_comp = mon.get("positions_with_competitors", 0)
    return (
        "🆚 <b>Конкуренты (OLX)</b>\n"
        f"  🔎 Позиций с конкурентами: {with_comp}\n"
        f"  ⬇️ Ниже рынка: {below} · ⬆️ Выше: {above} · 🕳 Без конкуренции: {no_comp}"
    )


def freelance_block() -> str:
    tasks = _load("freelance_tasks.json", [])
    if not tasks:
        return "💼 Фриланс: нет данных"
    ready = [t for t in tasks if t.get("status") == "PROPOSAL_READY"]
    notified = [t for t in ready if t.get("approval_notified")]
    total_usd = sum(float(t.get("budget_usd", 0)) for t in ready)
    return (
        "💼 <b>Фриланс</b>\n"
        f"  📝 Готово предложений: {len(ready)} (≈ ${_fmt(total_usd)})\n"
        f"  📨 Уведомлено в TG: {len(notified)} (ждут твоего approve)"
    )


def system_block() -> str:
    loadavg = "—"
    mem = "—"
    try:
        la = os.getloadavg()
        loadavg = f"{la[0]:.1f} / {la[1]:.1f} / {la[2]:.1f}"
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                k, _, v = line.partition(":")
                meminfo[k] = int(v.strip().split()[0]) // 1024  # MB
        total = meminfo.get("MemTotal", 0)
        avail = meminfo.get("MemAvailable", 0)
        pct = int((total - avail) / total * 100) if total else 0
        mem = f"{pct}% занято ({avail} МБ свободно)"
    except Exception:
        pass
    return (
        "🖥 <b>Система</b>\n"
        f"  ⚙️ Load: {loadavg}\n"
        f"  🧠 RAM: {mem}"
    )


def render_dashboard() -> str:
    blocks = [
        warehouse_block(),
        competitors_block(),
        freelance_block(),
        system_block(),
    ]
    return "\n\n".join(blocks)


def _handle_dashboard_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in _TRIGGERS):
        return False
    try:
        txt = "📊 <b>AIOS — Сводка</b>\n\n" + render_dashboard()
        api.send_message(chat_id, txt)
    except Exception:
        api.send_message(chat_id, render_dashboard().replace("<b>", "").replace("</b>", ""))
    return True


def _handle_freelance_summary_intent(api, chat_id: int, text: str) -> bool:
    """«фриланс», «что по фрилансу» — краткая сводка фриланс-воронки."""
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in _FREELANCE_TRIGGERS):
        return False
    tasks = _load("freelance_tasks.json", [])
    if not tasks:
        api.send_message(chat_id, "💼 Фриланс: данных пока нет.")
        return True
    ready = [x for x in tasks if x.get("status") == "PROPOSAL_READY"]
    notified = [x for x in ready if x.get("approval_notified")]
    bid = [x for x in tasks if x.get("status") == "BID_SUBMITTED"]
    lost = [x for x in tasks if x.get("status") == "LOST"]
    total = sum(float(x.get("budget_usd", 0)) for x in ready)
    lines = [
        "💼 <b>Фриланс-воронка</b>",
        f"  📝 Предложений готово: <b>{len(ready)}</b> (≈ ${_fmt(total)})",
        f"  📨 Уведомлено в TG (ждут approve): <b>{len(notified)}</b>",
        f"  🎯 Отправлено ставок: <b>{len(bid)}</b> · Проиграно: {len(lost)}",
        "",
        "💡 <i>Для отправки ставки вручную — открой уведомление в чате или напиши боту.</i>",
    ]
    try:
        api.send_message(chat_id, "\n".join(lines))
    except Exception:
        api.send_message(chat_id, "\n".join(lines).replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))
    return True
