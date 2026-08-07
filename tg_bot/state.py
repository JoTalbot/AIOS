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


_last_photo: dict[int, str] = {}


_photo_pending: dict[int, bool] = {}


_last_gen_ad: dict[int, str] = {}


_last_video: dict[int, str] = {}


_last_gmail_ids: dict[int, list[str]] = {}


_phone_route_drafts: dict[int, dict] = {}


_phone_brain_state: dict = {"ok": None, "checked": 0.0}


_last_phone_leads: dict[int, list[dict]] = {}


_last_phone_crm_tasks: dict[int, list[dict]] = {}


_last_bank_tasks: dict[int, list[dict]] = {}


_pending_actions: dict[int, str] = {}


_pending_confirmations: dict[int, str] = {}
