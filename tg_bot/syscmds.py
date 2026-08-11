"""Системные команды бота (выделено из run_telegram_bot.py).

Health, последний бэкап, история алертов, /start (живая сводка), /stats,
/status (платформы), /help.
"""
from __future__ import annotations

import json
from pathlib import Path

from tg_bot.common import _safe, _local_api_json


def cmd_system_health() -> str:
    data = _local_api_json("/api/system-health")
    lines = ["❤️ <b>System Health</b>", ""]
    lines.append(f"CPU: {data.get('cpu_percent')}%")
    lines.append(f"RAM: {data.get('memory_percent')}%")
    lines.append(f"Disk: {data.get('disk_percent')}%")
    for service in data.get("services", []):
        mark = "✅" if service.get("status") == "ok" else "❌"
        lines.append(f"{mark} {service.get('name')}: {service.get('status')}")
    return "\n".join(lines)


@_safe
def cmd_last_backup() -> str:
    data = _local_api_json("/api/backups")
    backups = data.get("backups", [])
    if not backups:
        return "💾 <b>Backup</b>\n\nЛокальных копий пока нет."
    item = backups[0]
    return "💾 <b>Last Backup</b>\n\n" + f"ID: <code>{item.get('backup_id', item.get('id'))}</code>\n" + f"Created: {item.get('created_at', '—')}\n" + f"Verified: {'✅' if item.get('verified') else '❌'}"


@_safe
def cmd_alert_history() -> str:
    path = Path("/var/lib/aios-health-alert/state.json")
    if not path.exists():
        return "🚨 <b>Alert History</b>\n\nНет сохранённых health-check данных."
    state = json.loads(path.read_text())
    failed = [name for name, value in state.items() if not value]
    return "🚨 <b>Alert History</b>\n\n" + ("✅ Текущие проверки в норме" if not failed else "❌ Проблемы: " + ", ".join(failed))


def cmd_start(first_name: str | None = None) -> str:
    """Приветствие с именем и живой сводкой по направлениям."""
    try:
        from tg_bot.dashboard import render_dashboard
        dash = render_dashboard()
        try:
            from tg_bot.common import _esc_tg as _esc_n
        except Exception:
            _esc_n = lambda x: str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        hi = f"👋 Привет, {_esc_n(first_name)}!" if first_name else "👋 Привет!"
        return (
            "🤖 <b>AIOS Control Panel</b>\n"
            f"{hi}\n"
            "Бот управления бизнесом и системой. Нажми кнопку меню или напиши текстом.\n\n"
            f"{dash}\n\n"
            "👇 <b>Разделы:</b> кнопки ниже"
        )
    except Exception:
        return "🤖 <b>AIOS Control Panel</b>\n\nВыберите раздел:"











@_safe
def cmd_stats() -> str:
    from aios_core.container import container

    db = container.db()
    orch = container.orchestrator()
    bm = container.backup_manager()
    db_stats = db.stats()
    orch_stats = orch.stats()
    bu_health = bm.health_report()

    tables_info = "\n".join(f"    <code>{t}</code>: {c} строк" for t, c in sorted(db_stats.get("tables", {}).items()))
    return (
        f"📊 <b>Статистика AIOS</b>\n\n"
        f"🗄️ <b>База данных</b>\n"
        f"  Путь: <code>{db_stats['db_path']}</code>\n"
        f"  Диалект: <code>{db_stats['dialect']}</code>\n"
        f"  Таблицы:\n{tables_info}\n\n"
        f"⚙️ <b>Оркестратор</b>\n"
        f"  Задач: {orch_stats.get('tasks', '?')}\n\n"
        f"💾 <b>Бэкапы</b>\n"
        f"  Всего: {bu_health['total_backups']}\n"
        f"  Размер: {bu_health['total_size_mb']} MB\n"
        f"  Директория: <code>{bu_health['backup_dir']}</code>"
    )


@_safe
def cmd_platforms() -> str:
    from aios_core.platforms import list_platforms

    plats = list_platforms()
    lines = [f"📱 <b>Платформы</b> ({len(plats)})\n"]
    lines.extend(f"  • <code>{p.name}</code> — <code>{p.android_package}</code>" for p in plats)
    return "\n".join(lines)


def _get_ads_db():
    from tg_bot.olx_cmds import _get_ads_db as _f
    return _f()


@_safe
def cmd_olx(args: str = "") -> str:
    from tg_bot.olx_cmds import cmd_olx as _f
    return _f(args)


@_safe
def cmd_olx_sub(args: str, chat_id: int, username: str | None, first_name: str | None) -> str:
    from tg_bot.olx_cmds import cmd_olx_sub as _f
    return _f(args, chat_id, username, first_name)


@_safe
def cmd_olx_unsub(args: str, chat_id: int) -> str:
    from tg_bot.olx_cmds import cmd_olx_unsub as _f
    return _f(args, chat_id)


@_safe
def cmd_olx_list(chat_id: int) -> str:
    from tg_bot.olx_cmds import cmd_olx_list as _f
    return _f(chat_id)


@_safe
def cmd_olx_latest(args: str, chat_id: int) -> str:
    from tg_bot.olx_cmds import cmd_olx_latest as _f
    return _f(args, chat_id)


@_safe
def cmd_olx_analytics(args: str) -> str:
    from tg_bot.olx_cmds import cmd_olx_analytics as _f
    return _f(args)


def cmd_help() -> str:
    return (
        "🤖 <b>AIOS Telegram Bot — Команды</b>\n\n"
        "  /start — приветствие\n"
        "  /stats — статистика БД и оркестратора\n  /ask <вопрос> — RAG: поиск по знаниям AIOS (проект, чаты, профиль)\n  /signals — ML/RL-сигналы по активам (консультирующие)\n"
        "  /status — зарегистрированные платформы\n"
        "  /olx — общая статистика OLX\n"
        "  /olx_sub &lt;запрос&gt; [min max] — подписка на новые объявления\n"
        "  /olx_unsub [запрос] — отписка (без аргументов = все)\n"
        "  /olx_list — мои подписки\n"
        "  /olx_latest &lt;запрос&gt; [N] — последние N объявлений\n"
        "  /olx_analytics &lt;запрос&gt; — AI-аналитика цен\n"
        "  /accounts — управление Google и Instagram аккаунтами\n"
        "  /google — быстрые команды Google (почта, календарь, диск)\n"
        "  /instagram — быстрые команды Instagram (профиль, посты)\n"
        "  /llm_mode [auto|gemini] — режим LLM в чате (балансер / Gemini Web)\n"
        "  /cmd &lt;команда&gt; — выполнить команду на сервере (root, /root/AIOS)\n"
        "  /skills — возможности системы (скилы, модули, адаптеры, команды)\n\n"
        "<i>Просто напишите боту обычным текстом, например:</i>\n"
        "  «проверь мою почту» · «сколько непрочитанных» · «кто я в гугле»\n"
        "  «покажи календарь» · «покажи мой инстаграм» · «мои посты» · «отправь письмо ...»\n\n"
        "<i>Бот работает в polling-режиме. Алерты приходят автоматически после каждого цикла сбора (каждые 30 мин).</i>"
    )




# ---------------------------------------------------------------------------
# Account control — Google + Instagram через обычный диалог
# ---------------------------------------------------------------------------

# Последнее фото, присланное пользователем (для будущих действий): chat_id -> путь
# Ждём описание детали после фото: chat_id -> True
# Последнее сгенерированное объявление OLX: chat_id -> part
# Последнее видео, присланное пользователем (для TikTok upload): chat_id -> путь
# Последние id писем, показанных в чате: chat_id -> [ids...]
# Ожидающие подтверждения действий: chat_id -> {"kind": ..., "data": ...}
# Короткоживущая навигация по уже подтверждённым черновикам маршрутов.






















# --------------------------------------------------------------- Голосовые ответы








# --------------------------------------------------------------- Шаблоны
TEMPLATES_FILE = PROJECT_ROOT / "data" / "templates.json"
REMINDERS_FILE = PROJECT_ROOT / "data" / "reminders.json"


