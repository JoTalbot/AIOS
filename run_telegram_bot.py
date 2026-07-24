#!/usr/bin/env python3
"""
AIOS Telegram Bot — управление агентами через Telegram.

Запуск::
    export AIOS_TELEGRAM_TOKEN="123456:ABC-DEF..."
    python run_telegram_bot.py

Команды:
    /start   — приветствие
    /stats   — статистика системы (БД, оркестратор, бэкапы)
    /status  — сводка по платформам
    /olx     — статистика OLX (объявления, цены)
    /help    — список команд

Архитектура:
    - Polling-режим (не нужен публичный URL)
    - Интегрируется с ``aios_core.container``
    - Без внешних зависимостей — чистые HTTP-запросы к Telegram API
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from typing import List

# ---------------------------------------------------------------------------
# Telegram API helpers (zero-dependency)
# ---------------------------------------------------------------------------


class TelegramAPI:
    """Minimal Telegram Bot API client (polling mode)."""

    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"

    def _request(self, method: str, data: dict | None = None) -> dict:
        url = f"{self._base}/{method}"
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def get_updates(self, offset: int = 0) -> list[dict]:
        result = self._request("getUpdates", {"offset": offset, "timeout": 30})
        return result.get("result", [])

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> dict:
        return self._request(
            "sendMessage",
            {"chat_id": chat_id, "text": text[:4000], "parse_mode": parse_mode},
        )


# ---------------------------------------------------------------------------
# Command handlers — каждая возвращает строку для отправки в чат
# ---------------------------------------------------------------------------


def _safe(fn):
    """Wrapper — catch all exceptions, return error string."""
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as exc:
            return f"❌ Ошибка: {exc}"
    return wrapper


@_safe
def cmd_start() -> str:
    return (
        "🤖 *AIOS Telegram Bot*\n\n"
        "Команды:\n"
        "  /stats  — статистика системы\n"
        "  /status — сводка по платформам\n"
        "  /olx    — статистика OLX\n"
        "  /help   — помощь\n\n"
        "_v9.3.1 · JoTalbot/AIOS_"
    )


@_safe
def cmd_stats() -> str:
    from aios_core.container import container

    db = container.db()
    orch = container.orchestrator()
    bm = container.backup_manager()
    db_stats = db.stats()
    orch_stats = orch.stats()
    bu_health = bm.health_report()

    tables_info = "\n".join(
        f"    `{t}`: {c} строк" for t, c in sorted(db_stats.get("tables", {}).items())
    )
    return (
        f"📊 *Статистика AIOS*\n\n"
        f"🗄️ *База данных*\n"
        f"  Путь: `{db_stats['db_path']}`\n"
        f"  Диалект: `{db_stats['dialect']}`\n"
        f"  Таблицы:\n{tables_info}\n\n"
        f"⚙️ *Оркестратор*\n"
        f"  Задач: {orch_stats.get('tasks', '?')}\n\n"
        f"💾 *Бэкапы*\n"
        f"  Всего: {bu_health['total_backups']}\n"
        f"  Размер: {bu_health['total_size_mb']} MB\n"
        f"  Директория: `{bu_health['backup_dir']}`"
    )


@_safe
def cmd_platforms() -> str:
    from aios_core.platforms import list_platforms

    plats = list_platforms()
    lines = [f"📱 *Платформы* ({len(plats)})\n"]
    for p in plats:
        lines.append(f"  • `{p.name}` — `{p.android_package}`")
    return "\n".join(lines)


@_safe
def cmd_olx() -> str:
    import sqlite3

    db_path = os.environ.get("AIOS_OLX_DB", "data/olx_default.sqlite")
    if not __import__("pathlib").Path(db_path).exists():
        return "⚠️ База OLX не найдена. Запустите `aios olx collect`."

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        total = conn.execute("SELECT COUNT(*) FROM olx_ads").fetchone()[0]
        if total == 0:
            return "📭 База OLX пуста. Запустите `aios olx collect --query ...`."

        # Top queries
        queries = conn.execute(
            "SELECT query, COUNT(*) as cnt FROM olx_ads GROUP BY query ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
        # Price stats
        price_row = conn.execute(
            "SELECT MIN(price), MAX(price), AVG(price) FROM olx_ads WHERE price > 0"
        ).fetchone()

        qlines = "\n".join(f"  `{q}`: {c} объявлений" for q, c in queries)
        return (
            f"🛒 *OLX Статистика*\n\n"
            f"  Всего объявлений: *{total}*\n"
            f"  Цены: мин *{price_row[0]}* · макс *{price_row[1]}* · "
            f"сред *{price_row[2]:.0f}* грн\n\n"
            f"📋 *Топ запросов:*\n{qlines}"
        )
    finally:
        conn.close()


@_safe
def cmd_help() -> str:
    return (
        "🤖 *AIOS Telegram Bot — Команды*\n\n"
        "  `/start`  — приветствие\n"
        "  `/stats`  — статистика БД и оркестратора\n"
        "  `/status` — зарегистрированные платформы\n"
        "  `/olx`    — статистика OLX (объявления, цены)\n"
        "  `/help`   — эта справка\n\n"
        "_Бот работает в polling-режиме._"
    )


# ---------------------------------------------------------------------------
# Main polling loop
# ---------------------------------------------------------------------------

COMMANDS = {
    "/start": cmd_start,
    "/stats": cmd_stats,
    "/status": cmd_platforms,
    "/olx": cmd_olx,
    "/help": cmd_help,
}


def run_bot(token: str) -> None:
    api = TelegramAPI(token)
    offset = 0

    print("🤖 AIOS Telegram Bot запущен")
    print(f"   Команды: {' '.join(COMMANDS)}")
    print("   Ожидание сообщений...\n")

    while True:
        try:
            updates = api.get_updates(offset)
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = (msg.get("text") or "").strip().split()[0]

                if not chat_id or not text:
                    continue

                handler = COMMANDS.get(text)
                if handler:
                    reply = handler()
                    api.send_message(chat_id, reply)
                    print(f"  → ответил на {text} (chat {chat_id})")
                else:
                    api.send_message(
                        chat_id, "ℹ️ Неизвестная команда. /help для списка."
                    )

        except KeyboardInterrupt:
            print("\n👋 Бот остановлен.")
            break
        except Exception as exc:
            print(f"⚠️ Ошибка polling: {exc}")
            time.sleep(5)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TOKEN = os.environ.get("AIOS_TELEGRAM_TOKEN")
    if not TOKEN:
        print("❌ Установите AIOS_TELEGRAM_TOKEN")
        print("   export AIOS_TELEGRAM_TOKEN='123456:ABC-DEF...'")
        sys.exit(1)

    run_bot(TOKEN)
