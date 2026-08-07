"""Общее изменяемое состояние Telegram-бота (разделяется монолитом и tg_bot/*).

ВНИМАНИЕ: эти объекты импортируются по ссылке — мутации видимы везде.
"""
from __future__ import annotations


_pending_confirm: dict[int, dict] = {}


_last_inbox: dict[int, list[dict]] = {}


_last_inbox_filters: dict[int, dict] = {}


_CHANNELS = {
    "gmail": ("✉️", "Почта"),
    "tg": ("✈️", "Telegram"),
    "ig": ("📸", "Instagram DM"),
    "messenger": ("💬", "Messenger"),
    "viber": ("💜", "Viber"),
    "signal": ("🔒", "Signal"),
    "android": ("📲", "Телефон"),
    "olx": ("🛒", "OLX"),
}
