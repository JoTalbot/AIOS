"""
AIOS Telegram Bot — управление агентами через Telegram.

Запуск production выполняется через systemd credentials; token не передаётся
через shell environment или аргументы процесса.

Команды:
    /start      — приветствие
    /stats      — статистика системы (БД, оркестратор, бэкапы)
    /status     — сводка по платформам
    /olx        — статистика OLX (объявления, цены)
    /olx_sub    — подписка на новые объявления по запросу
    /olx_unsub  — отписка
    /olx_list   — список моих подписок
    /olx_latest— последние объявления по подписке
    /olx_analytics — AI-аналитика цен по запросу
    /resend [ID] — контролируемый повтор failed_unknown
    /help       — список команд

Архитектура:
    - Polling-режим (не нужен публичный URL)
    - Интегрируется с ``aios_core.container``
    - Без внешних зависимостей — чистые HTTP-запросы к Telegram API
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import signal
import sys
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
from tg_bot.paths import state_path


def _redact_runtime_error(value: object) -> str:
    """Remove credentials and chat metadata from log errors."""
    from tg_bot.redaction import redact_runtime_text

    return redact_runtime_text(value, limit=500)


# === Inventory by photo v22.1 helpers ===
import random as _rnd

from tg_bot.inventory_photos import (  # noqa: E402
    _generate_draft_id, _build_inventory_keyboard, _process_expired_albums,
    _create_inventory_draft_and_ask_confirmation,
)


from tg_bot.common import _safe, _esc_tg, _run_account_control  # noqa: E402
from tg_bot.callbacks import _handle_callback, _handle_button  # noqa: E402
from tg_bot.llm import (  # noqa: E402
    _llm_chat, _cmd_skills, _cmd_llm_mode, _cmd_console, _llm_status,
    get_last_llm_metadata,
)
from tg_bot.outbox import TelegramOutbox  # noqa: E402
from tg_bot.generation_queue import TelegramGenerationQueue  # noqa: E402
from tg_bot.inbox import _llm_chat_direct, _parse_inbox_filters, _inbox_keyboard, _run_due_inbox, _collect_inbox, INBOX_SCHEDULE_FILE  # noqa: E402
from tg_bot.voice import VOICE_REPLY_FILE, _voice_enabled, _set_voice_enabled, _send_voice_reply, _transcribe_audio  # noqa: E402
from tg_bot.accounts import (  # noqa: E402
    _handle_account_intent, _llm_extract_gmail, _llm_extract_calendar,
    cmd_accounts, cmd_google, cmd_instagram, _acct_send_result, _acct_google, _acct_instagram, _fmt_gmail_list
)
from tg_bot.olx_cmds import (  # noqa: E402
    cmd_olx, cmd_olx_sub, cmd_olx_unsub, cmd_olx_list, cmd_olx_latest, cmd_olx_analytics
)
from tg_bot.treasury import _handle_treasury_intent  # noqa: E402
from tg_bot.phone import (  # noqa: E402
    _cancel_phone_pending, _confirm_phone_pending, _android_gateway_run,

    _handle_phone_brain_intent, _handle_phone_workflow_readiness_intent,
    _handle_phone_jobs_intent, _handle_phone_inventory_intent,
    _handle_phone_metrics_intent, _handle_phone_bank_monitor_intent,
    _handle_phone_recovery_intent, _handle_phone_weekly_report_intent,
    _handle_phone_control_center_intent, _handle_phone_audit_intent,
    _handle_phone_lead_intent, _handle_android_phone_workflow_intent,
    _handle_android_gateway_intent,
)
from tg_bot.inbox_router import _handle_unified_inbox_intent, _send_unified_inbox  # noqa: E402
from tg_bot.state import (  # noqa: E402
    _pending_confirm, _last_inbox, _last_inbox_filters, _last_photo,
    _photo_pending, _pending_actions, _pending_confirmations, _CHANNELS,
    _photo_albums, _inventory_drafts, _pending_inventory_edits, _pending_add_photo,
    _last_gen_ad, _last_video,
)


# Compatibility exports for the modular Telegram bot.  The public entrypoint
# historically exposed these helpers; keeping the aliases avoids breaking
# operator tooling while implementation lives in ``tg_bot`` modules.
from tg_bot import phone as _phone_module  # noqa: E402
from tg_bot.phone import (  # noqa: E402
    _followup_templates,
    _mask_android_notification,
    _parse_uklon_route_request,
    _phone_adapter,
    _phone_error,
    _phone_lead_queue,
    _send_phone_status,
    _uklon_next_route_field,
    _uklon_route_field_allowed,
    _uklon_route_field_label,
)
from tg_bot.inbox import (  # noqa: E402
    _format_inbox,
    _inbox_mark_read,
    _is_service_preview,
)
from tg_bot.callbacks import _handle_button_inner, _handle_inbox_callback  # noqa: E402
from tg_bot.keyboards import PHONE_MENU_KEYBOARD  # noqa: E402
from tg_bot.state import (  # noqa: E402
    _last_bank_tasks,
    _last_phone_crm_tasks,
    _last_phone_leads,
    _phone_route_drafts,
)

# These assignments intentionally remain visible in this entrypoint: recovery
# diagnostics extract this small bridge with ``ast`` without importing the bot.
_PHONE_BRAIN_API = os.environ.get("PHONE_BRAIN_API", "http://127.0.0.1:8790")
_phone_brain_state: dict[str, object] = {"ok": None, "checked": 0.0}

def _phone_brain_gateway_run(args: list[str], timeout: int) -> dict | None:
    """Выполнить команду Android-шлюза через очередь Phone Brain.

    Единая аренда устройства — никаких гонок процессов за ADB/экран.
    Возвращает dict как у legacy CLI, либо ``None``, если демон недоступен
    или команда не поддержана (тогда вызывающий код идёт legacy-путём).
    """
    import time as _time
    import urllib.request as _ureq

    plain = [str(a) for a in args if a != "--confirm"]
    command = plain[0] if plain else "status"
    confirmed = "--confirm" in args
    kind, payload = "", {}
    read_only = {"status", "apps", "profiles", "companion", "notifications", "accessibility",
                 "capture-status", "location-status", "files", "screenshot", "ui-dump", "audit"}
    if command in read_only and len(plain) == 1:
        kind, payload = "gateway.cli", {"command": command}
    elif command == "open" and len(plain) >= 2 and confirmed:
        kind, payload = "app.open", {"package": plain[1], "confirm": True}
    elif command == "location" and confirmed:
        kind, payload = "device.location", {"confirm": True}
    elif command == "pull" and len(plain) >= 2 and confirmed:
        kind, payload = "device.pull", {"path": plain[1], "confirm": True}
    else:
        return None  # команда не замаплена — legacy-путь

    now = _time.monotonic()
    if _phone_brain_state["ok"] is False and now - _phone_brain_state["checked"] < 20:
        return None

    def _api(method: str, path: str, body: dict | None = None, req_timeout: float = 4.0) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = _ureq.Request(_PHONE_BRAIN_API + path, data=data, method=method,
                                headers={"Content-Type": "application/json"})
        with _ureq.urlopen(request, timeout=req_timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        created = _api("POST", "/jobs", {"kind": kind, "payload": payload})
        job_id = int((created.get("job") or {}).get("id") or 0)
        if not job_id:
            return None
        _phone_brain_state.update(ok=True, checked=now)
    except Exception:
        _phone_brain_state.update(ok=False, checked=now)
        return None

    deadline = now + max(5, min(int(timeout), 240))
    while _time.monotonic() < deadline:
        try:
            job = _api("GET", f"/jobs/{job_id}").get("job") or {}
        except Exception:
            return None
        status = job.get("status")
        if status == "done":
            result = job.get("result") or {}
            if kind == "gateway.cli":
                output = result.get("output")
                if isinstance(output, dict):
                    return output
                return {"status": "error", "error": "пустой ответ очереди"}
            output = {"status": "ok"}
            for key, value in result.items():
                if key != "status":
                    output[key] = value
            return output
        if status in ("failed", "need_confirm", "cancelled"):
            return {"status": "error",
                    "error": str(job.get("error") or (job.get("result") or {}).get("error") or status)[:200]}
        _time.sleep(0.8)
    return {"status": "error", "error": "таймаут ожидания задачи Phone Brain"}


_phone_cancel_pending_impl = _cancel_phone_pending
_phone_confirm_pending_impl = _confirm_phone_pending
_phone_audit_impl = _handle_phone_audit_intent
_phone_bank_impl = _handle_phone_bank_monitor_intent
_phone_lead_impl = _handle_phone_lead_intent
_phone_workflow_impl = _handle_android_phone_workflow_intent
_phone_gateway_intent_impl = _handle_android_gateway_intent
_inbox_intent_impl = _handle_unified_inbox_intent


def _sync_phone_compat() -> None:
    """Propagate entrypoint overrides to the extracted implementation module."""
    _phone_module.PROJECT_ROOT = PROJECT_ROOT
    _phone_module._android_gateway_run = _android_gateway_run
    _phone_module._phone_adapter = _phone_adapter
    _phone_module._phone_lead_queue = _phone_lead_queue
    _phone_module._followup_templates = _followup_templates


def _cancel_phone_pending(api, chat_id: int, kind: str, data: dict) -> bool:
    _sync_phone_compat()
    return _phone_cancel_pending_impl(api, chat_id, kind, data)


def _confirm_phone_pending(api, chat_id: int, kind: str, data: dict) -> bool:
    _sync_phone_compat()
    return _phone_confirm_pending_impl(api, chat_id, kind, data)


def _handle_phone_audit_intent(api, chat_id: int, text: str) -> bool:
    _sync_phone_compat()
    return _phone_audit_impl(api, chat_id, text)


def _handle_phone_bank_monitor_intent(api, chat_id: int, text: str) -> bool:
    _sync_phone_compat()
    return _phone_bank_impl(api, chat_id, text)


def _handle_phone_lead_intent(api, chat_id: int, text: str) -> bool:
    _sync_phone_compat()
    return _phone_lead_impl(api, chat_id, text)


def _handle_android_phone_workflow_intent(api, chat_id: int, text: str) -> bool:
    _sync_phone_compat()
    return _phone_workflow_impl(api, chat_id, text)


# Keep identity with the extracted implementation for package consumers.
_handle_android_gateway_intent = _phone_gateway_intent_impl


def _handle_unified_inbox_intent(api, chat_id: int, text: str) -> bool:
    # Keep monkeypatch/operator overrides on the public entrypoint effective.
    from tg_bot import inbox_router as _router
    _router._inbox_mark_read = _inbox_mark_read
    return _inbox_intent_impl(api, chat_id, text)


from tg_bot.api import TelegramAPI  # noqa: E402
from tg_bot.keyboards import (  # noqa: E402
    ACCOUNTS_MENU_KEYBOARD,
    CODER_MENU_KEYBOARD,
    GOOGLE_MENU_KEYBOARD,
    INSTAGRAM_MENU_KEYBOARD,
    MAIN_MENU_INLINE,
)


@_safe
def cmd_system_health() -> str:
    from tg_bot.syscmds import cmd_system_health as _f
    return _f()


@_safe
def cmd_last_backup() -> str:
    from tg_bot.syscmds import cmd_last_backup as _f
    return _f()


@_safe
def cmd_alert_history() -> str:
    from tg_bot.syscmds import cmd_alert_history as _f
    return _f()


def cmd_start(first_name: str | None = None) -> str:
    from tg_bot.syscmds import cmd_start as _f
    return _f(first_name)


@_safe
def cmd_stats() -> str:
    from tg_bot.syscmds import cmd_stats as _f
    return _f()


@_safe
def cmd_platforms() -> str:
    from tg_bot.syscmds import cmd_platforms as _f
    return _f()


@_safe
def cmd_help() -> str:
    from tg_bot.syscmds import cmd_help as _f
    return _f()


TEMPLATES_FILE = state_path("templates.json")
REMINDERS_FILE = state_path("reminders.json")


def _load_templates() -> dict:
    from tg_bot.reminders import _load_templates as _f
    return _f()


def _save_templates(tpl: dict) -> None:
    from tg_bot.reminders import _save_templates as _f
    _f(tpl)


def _load_reminders() -> list[dict]:
    from tg_bot.reminders import _load_reminders as _f
    return _f()


def _save_reminders(items: list[dict]) -> None:
    from tg_bot.reminders import _save_reminders as _f
    _f(items)


def _handle_reminder(api, chat_id: int, text: str) -> None:
    from tg_bot.reminders import _handle_reminder as _f
    _f(api, chat_id, text)


def _run_due_reminders() -> int:
    from tg_bot.reminders import _run_due_reminders as _f
    return _f()



def _handle_sales_lifecycle_intent(api, chat_id: int, text: str) -> bool:
    from tg_bot.sales import _handle_sales_lifecycle_intent as _f
    return _f(api, chat_id, text)


def _send_unified_inbox(api, chat_id: int, text: str = "", filters: dict | None = None,
                       refresh: bool = False) -> None:
    from tg_bot.inbox_router import _send_unified_inbox as _f
    _f(api, chat_id, text, filters, refresh)


def _handle_unified_inbox_intent(api, chat_id: int, text: str) -> bool:
    from tg_bot import inbox_router as _router
    # Preserve the historical public override points after modularisation.
    _router._inbox_mark_read = _inbox_mark_read
    return _router._handle_unified_inbox_intent(api, chat_id, text)


def _handle_freelance_intent(api, chat_id: int, text: str) -> bool:
    from tg_bot.freelance import _handle_freelance_intent as _f
    return _f(api, chat_id, text)


def _get_coder_module():
    from tg_bot.coder import _get_coder_module as _f
    return _f()


@_safe
def cmd_coder_status() -> str:
    from tg_bot.coder import cmd_coder_status as _f
    return _f()


@_safe
def cmd_code_generate(args: str) -> str:
    from tg_bot.coder import cmd_code_generate as _f
    return _f(args)


@_safe
def cmd_code_review(args: str) -> str:
    from tg_bot.coder import cmd_code_review as _f
    return _f(args)


@_safe
def cmd_code_fix(args: str) -> str:
    from tg_bot.coder import cmd_code_fix as _f
    return _f(args)



def parse_command(text: str) -> tuple[str, str]:
    """Split '/command args' into (command, args)."""
    text = (text or "").strip()
    if not text:
        return "", ""
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0]  # strip @botname
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args


# State storage for callback interactions (chat_id -> pending action)
_paused = False




























# Button text -> action mapping
BUTTON_ACTIONS = {
    # Main menu
    "🧠 Кодер": "menu_coder",
    "📊 Статистика": "menu_stats",
    "🛒 OLX": "menu_olx",
    "📱 Платформы": "menu_platforms",
    "📲 Телефон": "menu_phone",
    "📲 Центр телефона": "phone_center",
    "🛠 Восстановление": "phone_recovery",
    "📥 Лиды телефона": "phone_leads",
    "📌 CRM задачи": "phone_crm_tasks",
    "🏦 Банки телефона": "phone_banks",
    "📈 Тренды телефона": "phone_trends",
    "🔄 Синхронизации": "phone_sync",
    "📋 Журнал телефона": "phone_audit",
    "🚕 Маршруты": "phone_routes",
    "🧩 Калибровки": "phone_calibrations",
    "🗄 Здоровье данных": "phone_data_health",
    "📦 Инвентарь": "phone_inventory",
    "📤 Экспорт метрик": "phone_metrics_export",
    "🧪 Сценарии": "phone_workflows",
    "🖥 Сервер": "menu_server",
    "🐳 Docker": "menu_docker",
    "🔑 API Ключи": "menu_keys",
    "📋 Логи": "menu_logs",
    "🤖 Бот": "menu_bot",
    "❓ Помощь": "menu_help",
    "◀️ Меню": "menu_back",
    # Coder menu
    "📋 Статус": "coder_status",
    "📦 Бэклог": "coder_backlog",
    "⚖️ Балансер": "coder_balancer",
    "📜 Git": "coder_git_status",
    "🔍 Review Bot": "coder_review_bot",
    "🔍 Review Coder": "coder_review_self",
    "✨ Написать код": "coder_gen_prompt",
    "🔧 Исправить": "coder_fix_prompt",
    "🚀 Push": "coder_git_push",
    "🔄 Перезапуск": "coder_restart",
    # OLX menu
    "📊 OLX Стат": "olx_stats",
    "📋 Подписки": "olx_list",
    "🆕 Последние": "olx_latest",
    "📈 Аналитика": "olx_analytics",
    # Accounts menu
    "🌐 Аккаунты": "menu_accounts",
    "🌐 Google": "accounts_google",
    "📸 Instagram": "accounts_instagram",
    "📘 Facebook": "accounts_facebook",
    "🎵 TikTok": "accounts_tiktok",
    "🛒 OLX": "accounts_olx",
    "◀️ Аккаунты": "accounts_back",
    # Google menu
    "✉️ Непрочитанные": "google_unread",
    "📥 Последние письма": "google_list",
    "🔍 Поиск письма": "google_search",
    "📧 Отправить письмо": "google_send",
    "👤 Кто я": "google_whoami",
    "📅 События": "google_events",
    "➕ Событие": "google_event_add",
    "📄 Документ": "google_docs",
    "📅 Календарь": "google_calendar",
    "🗂 Диск": "google_drive",
    "📷 Скрин почты": "google_mailshot",
    # Instagram menu
    "👤 Мой профиль": "ig_profile",
    "📈 Подписчики": "ig_stats",
    "🖼 Мои посты": "ig_posts",
    "📷 Скрин профиля": "ig_screenshot",
    "❤️ Лайкнуть": "ig_like_prompt",
    "👤 Подписка": "ig_follow_prompt",
    "💬 Директ": "ig_dm_prompt",
    # Bot menu
    "▶️ Старт": "bot_start",
    "⏸️ Пауза": "bot_pause",
    "🔄 Рестарт": "bot_restart",
    "⏹️ Стоп": "bot_stop",
    "📊 Статус бота": "bot_status",
    "🌐 Gemini Web": "bot_llm_gemini",
    "🔄 Балансер": "bot_llm_auto",
    "❤️ Health": "system_health",
    "💾 Backup": "last_backup",
    "🚨 Alerts": "alert_history",
}



def _allowed_chat_ids() -> set[int]:
    """Return the explicit Telegram operator allowlist from the environment."""
    from tg_bot.credentials import read_systemd_credential

    raw = os.environ.get("TELEGRAM_CHAT_ID", "") or read_systemd_credential(
        "telegram_owner_chat_id"
    )
    allowed: set[int] = set()
    for value in raw.split(","):
        try:
            allowed.add(int(value.strip()))
        except ValueError:
            continue
    return allowed


def _is_authorized_chat(chat_id: object) -> bool:
    try:
        return int(chat_id) in _allowed_chat_ids()
    except (TypeError, ValueError):
        return False


def run_bot(token: str) -> None:
    api = TelegramAPI(token)
    from tg_bot.metrics_exporter import start_metrics_exporter

    metrics_server = start_metrics_exporter()
    outbox = TelegramOutbox(api)
    outbox.start()

    def _process_generation_job(job: dict) -> bool:
        dedup_key = str(job["dedup_key"])
        chat_id = int(job["chat_id"])
        if outbox.seen(dedup_key):
            print(f"  [LLM] generated job already has outbound record ({dedup_key})")
            return True

        try:
            import threading as _threading

            def _show_typing(_chat_id):
                with contextlib.suppress(Exception):
                    api.send_chat_action(_chat_id)

            _threading.Thread(target=_show_typing, args=(chat_id,), daemon=True).start()
        except Exception:
            pass

        started = time.monotonic()
        reply = _llm_chat(chat_id, str(job["text"]))
        generation_sec = time.monotonic() - started
        route = get_last_llm_metadata()
        provider = str(route.get("provider") or "unknown")
        model = str(route.get("model") or "unknown")
        print(
            f"  [LLM] reply ({len(reply or '')} chars, provider={provider}, "
            f"model={model}, gen={generation_sec:.2f}s)"
        )
        if not reply:
            raise RuntimeError("empty LLM reply")

        import re as _re2
        reply = _re2.sub(r'<cmd>.*?</cmd>', '', reply, flags=_re2.DOTALL)
        reply = _re2.sub(r'```cmd\n.*?```', '', reply, flags=_re2.DOTALL).strip()
        if not reply:
            raise RuntimeError("empty sanitized LLM reply")

        on_sent = None
        if bool(job.get("voice_reply")):
            def _voice_after_text(_result, _chat_id=chat_id, _text=reply[:1500]):
                _send_voice_reply(api, _chat_id, _text)
            on_sent = _voice_after_text

        queued = outbox.enqueue(
            dedup_key=dedup_key,
            chat_id=chat_id,
            text=reply[:3900],
            parse_mode="",
            generation_sec=generation_sec,
            provider=provider,
            model=model,
            on_sent=on_sent,
            reply_to_message_id=job.get("source_message_id"),
        )
        if queued:
            print(f"  [LLM] queued ({dedup_key}); awaiting terminal send status")
        return queued or outbox.seen(dedup_key)

    generation_queue = TelegramGenerationQueue(_process_generation_job)
    generation_queue.start()
    offset = 0
    shutdown_requested = threading.Event()

    def _request_shutdown(_signum: int, _frame: object) -> None:
        shutdown_requested.set()
        # Interrupt long polling, periodic subprocess waits, or HTTP calls so
        # systemd does not have to wait for their individual network timeout.
        raise KeyboardInterrupt

    previous_handlers = {
        sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)
    }
    for sig in previous_handlers:
        signal.signal(sig, _request_shutdown)

    print("🤖 AIOS Telegram Bot запущен (v10.0 with inline menu)")
    print("   Ожидание сообщений...\n")

    _last_reminder_check = 0.0
    _last_inbox_check = 0.0

    while not shutdown_requested.is_set():
        try:
            # периодическая обработка альбомов (галерея)
            try:
                _process_expired_albums(api)
            except Exception:
                pass
            # проверка созревших напоминаний (раз в 60 сек)
            if time.time() - _last_reminder_check >= 60:
                try:
                    _run_due_reminders()
                except Exception as _rem_err:
                    print(f"  [REMINDER] check err: {_rem_err}")
                _last_reminder_check = time.time()

            # проверка расписания инбокса (раз в 60 сек)
            if time.time() - _last_inbox_check >= 60:
                try:
                    _run_due_inbox(token)
                except Exception as _ib_err:
                    print(f"  [INBOX] sched err: {_ib_err}")
                _last_inbox_check = time.time()

            updates = api.get_updates(offset)
            for upd in updates:
                if shutdown_requested.is_set():
                    break
                offset = upd["update_id"] + 1

                # Handle callback queries (button presses) — always process even when paused
                if "callback_query" in upd:
                    callback_chat = upd.get("callback_query", {}).get("message", {}).get("chat", {}).get("id")
                    if not _is_authorized_chat(callback_chat):
                        print("  [SECURITY] ignored callback from unauthorized chat")
                        continue
                    _handle_callback(api, upd)
                    continue

                # Skip messages if paused
                if _paused:
                    continue

                msg = upd.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                username = msg.get("from", {}).get("username")
                first_name = msg.get("from", {}).get("first_name")
                text = (msg.get("text") or "").strip()

                if not chat_id:
                    continue
                content_kind = "voice" if (msg.get("voice") or msg.get("audio")) else "text"
                print(f"📩 [TG INCOMING] kind={content_kind} chars={len(text)}")
                if not _is_authorized_chat(chat_id):
                    # Silent drop avoids turning the bot into an account oracle
                    # or amplification endpoint for arbitrary Telegram users.
                    print("  [SECURITY] ignored message from unauthorized chat")
                    continue

                # Голосовое сообщение — распознать и выполнить как команду
                if (msg.get("voice") or msg.get("audio")) and not text:
                    try:
                        fid = (msg.get("voice") or msg.get("audio") or {}).get("file_id", "")
                        if not fid:
                            continue
                        vpath = api.download_file_by_id(fid)
                        api.send_message(chat_id, "🎙 Распознаю голосовое…")
                        transcript = _transcribe_audio(vpath)
                        if not transcript:
                            api.send_message(chat_id, "😕 Не смог распознать речь. Попробуйте ещё раз.")
                            continue
                        api.send_message(chat_id, f"🎙 Услышал: <i>{_esc_tg(transcript[:300])}</i>")
                        handled = False
                        try:
                            handled = _handle_account_intent(api, chat_id, transcript)
                        except Exception as a_err:
                            print(f"  [VOICE] intent error: {a_err}")
                        if not handled:
                            voice_key = f"llm:{upd.get('update_id', msg.get('message_id', 'unknown'))}"
                            generation_queue.enqueue(
                                dedup_key=voice_key,
                                chat_id=chat_id,
                                text=transcript,
                                source_message_id=msg.get("message_id"),
                                voice_reply=_voice_enabled(chat_id),
                            )
                        print(f"  [VOICE] transcript queued ({len(transcript)} chars)")
                    except Exception as v_err:
                        print(f"  [VOICE] error: {v_err}")
                        try:
                            api.send_message(chat_id, f"❌ Ошибка обработки голосового: {v_err}")
                        except Exception:
                            pass
                    continue

                # Видео от пользователя — сохранить для TikTok upload
                if (msg.get("video") or msg.get("video_note") or msg.get("animation")) and not text:
                    try:
                        src = msg.get("video") or msg.get("video_note") or msg.get("animation") or {}
                        fid = src.get("file_id", "")
                        if fid:
                            path = api.download_file_by_id(fid)
                            _last_video[chat_id] = path
                            api.send_message(chat_id,
                                             "🎬 Видео получил! Напишите «опубликуй видео в тикток <описание>» — "
                                             "и я опубликую его (с подтверждением).")
                        else:
                            api.send_message(chat_id, "❌ Не смог получить видео.")
                    except Exception as v_err:
                        print(f"  [VIDEO] error: {v_err}")
                        try:
                            api.send_message(chat_id, f"❌ Ошибка загрузки видео: {v_err}")
                        except Exception:
                            pass
                    continue

                                # Фото от пользователя — создание товара на складе по фото (v22.1 с галереей и подтверждением)
                if msg.get("photo"):
                    try:
                        file_id = msg["photo"][-1].get("file_id", "")
                        caption = (msg.get("caption") or "").strip()
                        text_from_caption = caption or text
                        media_group_id = msg.get("media_group_id")  # для альбомов
                        if not file_id:
                            api.send_message(chat_id, "❌ Не смог получить фото.")
                            continue
                        path = api.download_file_by_id(file_id)
                        _last_photo[chat_id] = path

                        # Если пользователь сейчас добавляет фото к существующему черновику
                        if chat_id in _pending_add_photo and not media_group_id:
                            d_id = _pending_add_photo.get(chat_id)
                            draft = _inventory_drafts.get(d_id)
                            if draft:
                                if path not in draft["photos"]:
                                    draft["photos"].append(path)
                                api.send_message(chat_id,
                                    f"📸 Добавил фото к черновику «{_esc_tg(draft.get('name')[:40])}» (теперь {len(draft['photos'])} шт).\n"
                                    f"Пришлите ещё или нажмите ✅ Подтвердить.",
                                    reply_markup=_build_inventory_keyboard(d_id, draft.get("price",0), len(draft["photos"])))
                                continue
                            else:
                                _pending_add_photo.pop(chat_id, None)

                        # Альбомы: собираем в _photo_albums и ждём 2.5 сек
                        if media_group_id:
                            album = _photo_albums.get(media_group_id)
                            if not album:
                                _photo_albums[media_group_id] = {"chat_id": chat_id, "photos": [path], "caption": caption, "ts": time.time(), "processed": False}
                            else:
                                if path not in album["photos"]:
                                    album["photos"].append(path)
                                if caption and not album.get("caption"):
                                    album["caption"] = caption
                                album["ts"] = time.time()
                            # если это альбом для добавления к черновику, обработается в _process_expired_albums
                            # пока просто ждём
                            continue

                        # Проверка явного запроса объявления (не склада)
                        lc = (text_from_caption or "").lower()
                        explicit_ad = any(w in lc for w in ("объявление из фото","объявление по фото","выложи по фото","сделай объявление из фото"))
                        if explicit_ad and "склад" not in lc and "деталь" not in lc and "товар" not in lc and "запчасть" not in lc:
                            api.send_message(chat_id, "📸 Фото получил и сохранил! Опишите деталь — сгенерирую объявление.")
                            _photo_pending[chat_id] = True
                            continue

                        # Одиночное фото — создаём черновик с подтверждением
                        api.send_message(chat_id, "📸 Фото получил! Распознаю деталь... ⏳ ~10-20 сек")
                        _create_inventory_draft_and_ask_confirmation(api, chat_id, [path], caption)

                    except Exception as ph_err:
                        print(f"  [PHOTO_INV v22.1] error: {ph_err}")
                        import traceback as _tb; _tb.print_exc()
                        try:
                            api.send_message(chat_id, f"❌ Ошибка обработки фото: {_esc_tg(str(ph_err)[:200])}")
                        except:
                            pass
                    continue

                # Обработка истёкших альбомов (галерея) — делаем после каждого сообщения тоже
                try:
                    _process_expired_albums(api)
                except Exception as ae:
                    print(f"album process err: {ae}")

                if not text:
                    continue

                # ---- Редактирование полей черновика склада (цена/название/кол-во/категория) ----
                if chat_id in _pending_inventory_edits and text:
                    try:
                        edit_info = _pending_inventory_edits.get(chat_id, {})
                        draft_id = edit_info.get("draft_id")
                        field = edit_info.get("field")
                        draft = _inventory_drafts.get(draft_id)
                        if not draft:
                            _pending_inventory_edits.pop(chat_id, None)
                            api.send_message(chat_id, "❌ Черновик не найден (истёк). Пришлите фото заново.")
                            continue
                        new_val = text.strip()
                        if field == "price":
                            # принимаем "1500", "1 500 грн", "1,5k" не поддерживаем, просто число
                            cleaned = re.sub(r"[^\d.,]", "", new_val).replace(",", ".")
                            try:
                                price = float(cleaned)
                                if price < 0 or price > 1000000:
                                    raise ValueError("цена вне диапазона")
                                draft["price"] = price
                            except Exception as e:
                                api.send_message(chat_id, f"❌ Не понял цену «{new_val}». Введите число, например: 1500")
                                continue
                        elif field == "qty":
                            m = re.search(r"\d+", new_val)
                            if not m:
                                api.send_message(chat_id, f"❌ Не понял количество «{new_val}». Введите число, например: 2")
                                continue
                            draft["qty"] = max(1, int(m.group()))
                        elif field == "name":
                            if len(new_val) < 2:
                                api.send_message(chat_id, "❌ Название слишком короткое.")
                                continue
                            draft["name"] = new_val[:120]
                        elif field == "category":
                            draft["category"] = new_val[:40]
                        else:
                            api.send_message(chat_id, f"❌ Неизвестное поле {field}")
                            continue
                        _pending_inventory_edits.pop(chat_id, None)
                        # показываем обновлённый черновик
                        kb = _build_inventory_keyboard(draft_id, draft["price"], len(draft["photos"]))
                        lines = [
                            f"✏️ Обновил <b>{field}</b>: {_esc_tg(str(new_val)[:80])}",
                            f"📦 <b>{_esc_tg(draft['name'])}</b> · {draft['qty']} шт · {draft['price']} грн",
                            f"🏷 { _esc_tg(draft['category']) } · 📸 {len(draft['photos'])} фото",
                            "",
                            "Подтвердите:"
                        ]
                        api.send_message(chat_id, "\n".join(lines), reply_markup=kb)
                    except Exception as e_edit:
                        print(f"edit err {e_edit}")
                        api.send_message(chat_id, f"❌ Ошибка редактирования: {e_edit}")
                    continue

                # Handle pending actions from inline buttons
                if not text:
                    continue

                # Handle pending actions from inline buttons
                if chat_id in _pending_actions:
                    action = _pending_actions.pop(chat_id)
                    reply = None
                    if action == "gen_code":
                        reply = cmd_code_generate(text)
                    elif action == "fix_bug":
                        reply = cmd_code_fix(text)
                    if reply:
                        api.send_message(chat_id, reply)
                        print(f"  → action {action}")
                    continue

                cmd, args = parse_command(text)
                if not cmd.startswith("/"):
                    # Check if it is a button press
                    btn_action = BUTTON_ACTIONS.get(text)

                    # Handle pending actions first
                    if chat_id in _pending_actions and not btn_action:
                        action = _pending_actions.pop(chat_id)
                        reply = None
                        if action == "gen_code":
                            reply = cmd_code_generate(text)
                        elif action == "fix_bug":
                            reply = cmd_code_fix(text)
                        if reply:
                            api.send_message(chat_id, reply)
                        continue

                    if btn_action:
                        # Handle button press same as callback
                        _handle_button(api, chat_id, btn_action)
                        print(f"  -> button {btn_action}")
                        continue

                    # Natural language control of Google / Instagram accounts
                    try:
                        from tg_bot.calls import _handle_calls_intent
                        if _handle_calls_intent(api, chat_id, text):
                            print("  -> calls-intent handled")
                            continue
                        if _handle_account_intent(api, chat_id, text):
                            print("  -> account-intent handled")
                            continue
                    except Exception as acct_err:
                        import traceback as _tb2
                        _tb2.print_exc()
                        try:
                            api.send_message(chat_id, f"❌ Ошибка управления аккаунтом: {acct_err}")
                        except Exception:
                            pass

                    # --- AIOS Autonomy: исполнение бизнес-команд владельца (опт-ин) ---
                    _skip_autonomy = False
                    try:
                        from aios_core.llm_gemini_web import get_llm_mode as _glm2
                        _skip_autonomy = _glm2(chat_id) == "gemini"
                    except Exception:
                        pass
                    if os.environ.get("AIOS_AUTONOMY_HOOK") == "1" and not _skip_autonomy:
                        try:
                            if "_auto_core" not in globals():
                                from aios_core.autonomy import AutonomyCore as _AutoCore
                                globals()["_auto_core"] = _AutoCore()
                            _ao = globals()["_auto_core"].process_owner(
                                chat_id, text, execute_reply=False
                            )
                            _is_action = _ao.get("mode") == "action" and _ao.get("action") not in ("reply_customer", "query_platform")
                            if _is_action or _ao.get("mode") == "manual":
                                _txt = _ao.get("text") or ""
                                if _ao.get("mode") == "manual" and _ao.get("approval_id"):
                                    _txt = (_txt or "Действие требует подтверждения") + "\nID: <code>" + str(_ao.get("approval_id")) + "</code>"
                                if _txt:
                                    try:
                                        api.send_message(chat_id, _txt[:3900])
                                    except Exception:
                                        try:
                                            api.send_message(chat_id, _txt[:3900], parse_mode="")
                                        except Exception:
                                            pass
                                print(f"  [AUTONOMY] {_ao.get('action')} -> {_ao.get('decision')}")
                                continue
                        except Exception as _au_err:
                            print(f"  [AUTONOMY] err: {_au_err}")

                    # Persist generation and return to polling immediately. One
                    # sequential worker per chat preserves conversational order;
                    # different chats can generate concurrently.
                    dedup_key = f"llm:{upd.get('update_id', msg.get('message_id', 'unknown'))}"
                    queued = generation_queue.enqueue(
                        dedup_key=dedup_key,
                        chat_id=chat_id,
                        text=text,
                        source_message_id=msg.get("message_id"),
                        voice_reply=_voice_enabled(chat_id),
                    )
                    if queued:
                        print(f"  [LLM] generation queued ({dedup_key}); polling continues")
                    else:
                        print(f"  [LLM] duplicate generation skipped ({dedup_key})")
                    continue

                reply = None
                keyboard = None

                if cmd == "/start" or cmd == "/menu":
                    reply = cmd_start(first_name)
                    keyboard = MAIN_MENU_INLINE
                elif cmd == "/backtest" or cmd == "/bt":
                    # Бэктест ML/RL стратегий
                    reply = None
                    keyboard = None
                    sym = (args or "BTC").strip().upper().split()[0]
                    api.send_message(chat_id, f"📈 Бэктест {sym} (ML/RL стратегии)…")
                    try:
                        import subprocess as _sp_bt
                        _r = _sp_bt.run(
                            ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "aios_core" / "quant" / "backtest_ai_strategies.py"),
                             "--symbol", sym, "--json"],
                            capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
                        _out = (_r.stdout or "").strip()
                        import json as _json
                        try:
                            d = _json.loads(_out)
                        except Exception:
                            api.send_message(chat_id, "❌ Не удалось бэктестить. Проверьте символ.")
                            continue
                        lines = [f"📈 <b>Бэктест {sym}</b>\n"]
                        for strat, m in d.items():
                            if strat == "symbol" or not isinstance(m, dict) or "error" in m:
                                continue
                            lines.append(f"<b>{strat}:</b>")
                            lines.append(f"   • Доходность: {m.get('total_return_pct','?')}%")
                            lines.append(f"   • Sharpe: {m.get('sharpe','?')} · Sortino: {m.get('sortino','?')}")
                            lines.append(f"   • Max DD: {m.get('max_drawdown_pct','?')}% · Win: {m.get('win_rate_pct','?')}%")
                            if m.get('ml_prob_up'):
                                lines.append(f"   • ML prob_up: {m.get('ml_prob_up')}")
                        api.send_message(chat_id, "\n".join(lines)[:3900])
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка бэктеста: {e}")
                    continue
                elif cmd == "/signals" or cmd == "/signal":

                    # ML + RL консультирующие сигналы
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "📊 Собираю ML/RL-сигналы…")
                    try:
                        from aios_core.quant_trading_engine import get_ai_signal_summary
                        d = get_ai_signal_summary()
                        ml = d.get("ml", {})
                        rl = d.get("rl", {})
                        lines = ["📊 <b>AIOS Quant Сигналы</b>\n"]
                        lines.append("🔮 <b>ML (CatBoost):</b>")
                        lines.append(f"   • Активов: {ml.get('total', 0)}")
                        lines.append(f"   • Бычьих: <b>{ml.get('bullish_strong', 0)}</b> · Медвежьих: {ml.get('bearish_strong', 0)}")
                        top = ml.get("top_momentum", [])
                        if top:
                            lines.append(f"   • Топ-моментум: {', '.join(top)}")
                        lines.append("")
                        lines.append("🤖 <b>RL (PPO):</b>")
                        rl_long = rl.get("long", [])
                        rl_half = rl.get("half", [])
                        lines.append(f"   • LONG: {', '.join(rl_long) if rl_long else '—'}")
                        lines.append(f"   • HALF (0.5): {', '.join(rl_half) if rl_half else '—'}")
                        lines.append("")
                        lines.append("<i>Консультирующие сигналы. Не финансовая рекомендация.</i>")
                        api.send_message(chat_id, "\n".join(lines)[:3900])
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка сигналов: {e}")
                    continue
                elif cmd == "/ask" or cmd == "/rag":

                    # RAG-запрос к знаниям AIOS (проект + чаты + профиль владельца)
                    reply = None
                    keyboard = None
                    question = (args or "").strip()
                    if not question:
                        api.send_message(chat_id, "❓ Задайте вопрос через /ask <ваш вопрос>\nПример: /ask кто владелец AIOS")
                        continue
                    api.send_message(chat_id, "🔎 Ищу в базе знаний AIOS…")
                    try:
                        import subprocess as _sp_ask
                        _r = _sp_ask.run(
                            ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "aios_ask.py"),
                             question, "--llm", "--top", "5"],
                            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
                        _out = (_r.stdout or "").strip()
                        # берём ответ LLM (после маркера "=== Ответ LLM ===")
                        if "=== Ответ LLM ===" in _out:
                            _ans = _out.split("=== Ответ LLM ===")[-1].strip()
                        else:
                            _ans = _out[-2000:]
                        if _ans:
                            api.send_message(chat_id, _ans[:3900])
                        else:
                            api.send_message(chat_id, "🤷 Не нашёл ответа. Сформулируйте иначе.")
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка RAG: {e}")
                    continue
                elif cmd == "/stats":
                    reply = cmd_stats()
                elif cmd in ("/status", "/platforms"):
                    reply = cmd_platforms()
                elif cmd in ("/calls", "/whisper"):
                    from tg_bot.calls import _handle_calls_intent
                    _handle_calls_intent(api, chat_id, "/calls")
                    continue
                elif cmd == "/olx":
                    reply = cmd_olx(args)
                elif cmd == "/olx_sub" or cmd == "/subscribe":
                    reply = cmd_olx_sub(args, chat_id, username, first_name)
                elif cmd == "/olx_unsub" or cmd == "/unsubscribe":
                    reply = cmd_olx_unsub(args, chat_id)
                elif cmd == "/olx_list" or cmd == "/mysubs":
                    reply = cmd_olx_list(chat_id)
                elif cmd == "/olx_latest" or cmd == "/latest":
                    reply = cmd_olx_latest(args, chat_id)
                elif cmd == "/olx_analytics" or cmd == "/analytics":
                    reply = cmd_olx_analytics(args)
                elif cmd in ("/reputation", "/rep", "/clients"):
                    reply = None
                    keyboard = None
                    import subprocess as _sp_rep
                    try:
                        r = _sp_rep.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_autonomy_clients.py"),
                                         "--top", "15"], capture_output=True, text=True,
                                        timeout=60, cwd=str(PROJECT_ROOT))
                        api.send_message(chat_id, (r.stdout or "нет данных")[:3800])
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка: {e}")
                elif cmd in ("/security", "/sec", "/safe"):
                    reply = None
                    keyboard = None
                    import subprocess as _sp_sec
                    try:
                        r = _sp_sec.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_autonomy_security.py")],
                                        capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
                        api.send_message(chat_id, (r.stdout or "нет данных")[:3800])
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка: {e}")
                elif cmd in ("/bank", "/banks"):
                    reply = None
                    keyboard = None
                    bank = args.strip().lower()
                    if bank not in ("abank", "privat"):
                        api.send_message(chat_id, "Банки: <b>abank</b>, <b>privat</b>.\n"
                                                   "Пример: /bank privat balance · /bank abank balance")
                    else:
                        api.send_message(chat_id, f"⏳ Проверяю {bank}…")
                        import subprocess as _sp_b
                        try:
                            r = _sp_b.run(["xvfb-run", "-a", "-s", "-screen 0 1440x900x24",
                                           "/opt/aios/.venv/bin/python",
                                           str(PROJECT_ROOT / "run_account_control.py"),
                                           bank, "balance"], capture_output=True, text=True,
                                          timeout=200, cwd=str(PROJECT_ROOT))
                            out = (r.stdout or "нет данных")[-600:]
                            api.send_message(chat_id, f"🏦 <b>{bank}</b>\n<code>{out[:3800]}</code>")
                        except Exception as e:
                            api.send_message(chat_id, f"❌ Ошибка: {e}")
                elif cmd == "/digest":
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "⏳ Собираю дайджест…")
                    import subprocess as _sp
                    try:
                        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_digest.py"),
                                     "--chat", str(chat_id)],
                                    capture_output=True, text=True, timeout=200, cwd=str(PROJECT_ROOT))
                        if "Дайджест отправлен" in (r.stdout or ""):
                            api.send_message(chat_id, "✅ Дайджест отправлен ☀️")
                        else:
                            api.send_message(chat_id, "❌ Не удалось собрать дайджест: "
                                                      f"{(r.stderr or r.stdout or '?')[-250:]}")
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка дайджеста: {e}")
                elif cmd == "/accounts":
                    reply = cmd_accounts()
                    keyboard = ACCOUNTS_MENU_KEYBOARD
                elif cmd == "/google":
                    if args.strip():
                        sub_a = args.strip().lower().split()[0]
                        reply = None
                        keyboard = None
                        if sub_a in ("whoami",):
                            _acct_google(api, chat_id, "whoami")
                        elif sub_a in ("unread", "unseen"):
                            _acct_google(api, chat_id, "unread")
                        elif sub_a in ("list", "emails"):
                            _acct_google(api, chat_id, "list")
                        elif sub_a in ("calendar", "cal"):
                            _acct_google(api, chat_id, "calendar")
                        elif sub_a in ("drive",):
                            _acct_google(api, chat_id, "drive")
                        elif sub_a in ("mailshot", "shot"):
                            _acct_google(api, chat_id, "mailshot")
                        elif sub_a in ("send",):
                            _acct_google(api, chat_id, "send_prompt")
                        elif sub_a in ("events", "event", "cal_events"):
                            _acct_google(api, chat_id, "events")
                        elif sub_a in ("event_add", "eventadd"):
                            _acct_google(api, chat_id, "event_prompt")
                        elif sub_a in ("docs", "doc"):
                            _acct_google(api, chat_id, "docs_prompt")
                        elif sub_a in ("search", "find"):
                            q = args.strip().split(None, 1)[1] if len(args.strip().split(None, 1)) > 1 else ""
                            if q:
                                data = _run_account_control(["google", "gmail_search", q, "5"])
                                if data.get("status") == "ok":
                                    api.send_message(chat_id, _fmt_gmail_list(data)
                                                     if data.get("emails")
                                                     else f"🔍 По запросу «{q}» писем не найдено.")
                                else:
                                    api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                                reply = None
                                keyboard = None
                            else:
                                reply = cmd_google(args)
                        else:
                            reply = cmd_google(args)
                    else:
                        reply = cmd_google("")
                        keyboard = GOOGLE_MENU_KEYBOARD
                elif cmd in ("/fb", "/facebook"):
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "⏳ Facebook…")
                    data = _run_account_control(["facebook", "profile"])
                    if data.get("status") == "ok":
                        f = data.get("facebook", {})
                        txt = (f"📘 <b>Facebook</b>\n👤 {_esc_tg(f.get('name'))}\n"
                               f"🔗 {f.get('profile_url')}\n🔔 Уведомлений: {f.get('notifications') or 0}")
                        _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                         "screenshot": f.get("screenshot"),
                                                         "caption": "📘 Facebook"}, "")
                    else:
                        api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                elif cmd == "/tiktok":
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "⏳ TikTok…")
                    data = _run_account_control(["tiktok", "profile"])
                    if data.get("status") == "ok":
                        p = data.get("tiktok", {})
                        txt = (f"🎵 <b>TikTok</b>\n👤 {_esc_tg(p.get('name') or p.get('username'))}\n"
                               f"👥 Подписчики: {p.get('followers') or 0} · 🔄 Подписки: {p.get('following') or 0}\n"
                               f"❤️ Лайки: {p.get('likes') or 0}\n🔗 {p.get('profile_url')}")
                        _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                         "screenshot": p.get("screenshot"),
                                                         "caption": "🎵 TikTok"}, "")
                    else:
                        api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                elif cmd == "/olx_account":
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "⏳ OLX…")
                    data = _run_account_control(["olx", "profile"])
                    if data.get("status") == "ok":
                        o = data.get("olx", {})
                        txt = (f"🛒 <b>OLX</b>\n👤 {_esc_tg(o.get('name') or '?')}\n"
                               f"📄 Объявлений: {o.get('ads_count') or 0}\n"
                               f"💰 Баланс: {o.get('balance') or 0} грн")
                        _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                         "screenshot": o.get("screenshot"),
                                                         "caption": "🛒 OLX"}, "")
                    else:
                        api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                elif cmd == "/instagram":
                    if args.strip():
                        sub_a = args.strip().lower().split()[0]
                        reply = None
                        keyboard = None
                        if sub_a in ("profile", "me"):
                            _acct_instagram(api, chat_id, "profile")
                        elif sub_a in ("stats", "stat"):
                            _acct_instagram(api, chat_id, "stats")
                        elif sub_a in ("posts", "post"):
                            _acct_instagram(api, chat_id, "posts")
                        elif sub_a in ("screenshot", "shot"):
                            _acct_instagram(api, chat_id, "screenshot")
                        else:
                            reply = cmd_instagram(args)
                    else:
                        reply = cmd_instagram("")
                        keyboard = INSTAGRAM_MENU_KEYBOARD
                elif cmd == "/resend":
                    resend_arg = args.strip()
                    if resend_arg:
                        try:
                            uncertain_id = int(resend_arg)
                        except ValueError:
                            reply = "❌ Формат: <code>/resend ID</code>"
                        else:
                            if outbox.manual_resend(uncertain_id):
                                reply = f"✅ Повторная отправка для uncertain ID <code>{uncertain_id}</code> поставлена в очередь."
                            else:
                                reply = "❌ Запись не найдена, уже обработана или не имеет статуса failed_unknown."
                    else:
                        uncertain = outbox.list_uncertain(limit=10)
                        if not uncertain:
                            reply = "✅ Нет отправок со статусом failed_unknown."
                        else:
                            lines = ["⚠️ <b>Неопределённые отправки</b> (только метаданные):"]
                            for item in uncertain:
                                created = time.strftime(
                                    "%Y-%m-%d %H:%M:%S", time.localtime(float(item["created_at"]))
                                )
                                lines.append(
                                    f"• ID <code>{item['id']}</code> · chat <code>{item['chat_id']}</code> "
                                    f"· {created} · {item['error_class'] or 'unknown'}"
                                )
                            lines.append("\nПовторить явно: <code>/resend ID</code>")
                            reply = "\n".join(lines)
                elif cmd in ("/dead", "/retrygen"):
                    dead_arg = args.strip()
                    if cmd == "/retrygen":
                        try:
                            dead_id = int(dead_arg)
                        except ValueError:
                            reply = "❌ Формат: <code>/retrygen ID</code>"
                        else:
                            if generation_queue.requeue_dead_letter(dead_id):
                                reply = f"✅ Generation dead-letter ID <code>{dead_id}</code> явно возвращён в очередь."
                            else:
                                reply = "❌ Dead-letter запись не найдена или уже обработана."
                    else:
                        dead = generation_queue.list_dead_letters(limit=10)
                        if not dead:
                            reply = "✅ Generation dead-letter очередь пуста."
                        else:
                            lines = ["⚠️ <b>Generation dead-letter</b> (только метаданные):"]
                            for item in dead:
                                created = time.strftime(
                                    "%Y-%m-%d %H:%M:%S", time.localtime(float(item["created_at"]))
                                )
                                lines.append(
                                    f"• ID <code>{item['id']}</code> · attempts {item['attempts']} "
                                    f"· {created} · {item['error_class'] or 'unknown'}"
                                )
                            lines.append("\nПовторить явно: <code>/retrygen ID</code>")
                            reply = "\n".join(lines)
                elif cmd == "/help":
                    reply = cmd_help()
                elif cmd == "/coder":
                    reply = "🧠 <b>Агент-кодер MetaCognitiveCoder</b>\n\nУправление автономным кодером:"
                    keyboard = CODER_MENU_KEYBOARD
                elif cmd == "/llm_status":
                    reply = _llm_status()
                elif cmd in ("/llm_mode", "/gemini"):
                    reply = _cmd_llm_mode(args, chat_id)
                elif cmd == "/cmd":
                    reply = _cmd_console(args, chat_id)
                elif cmd == "/skills":
                    reply = _cmd_skills(api, chat_id)
                elif cmd == "/code":
                    reply = cmd_code_generate(args)
                elif cmd == "/review":
                    reply = cmd_code_review(args)
                elif cmd == "/fix":
                    reply = cmd_code_fix(args)
                else:
                    reply = "ℹ️ Неизвестная команда. Напишите /menu для навигации."

                if reply:
                    if keyboard:
                        api.send_message(chat_id, reply, reply_markup=keyboard)
                    else:
                        api.send_message(chat_id, reply)
                    print(f"  → ответил на {cmd}")

        except KeyboardInterrupt:
            shutdown_requested.set()
            break
        except Exception as exc:
            if shutdown_requested.is_set():
                break
            if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
                continue  # normal for long polling
            print(f"⚠️ Ошибка polling: {_redact_runtime_error(exc)}")
            time.sleep(3)

    drain_timeout = max(5.0, float(os.environ.get("TELEGRAM_DRAIN_TIMEOUT", "45")))
    print(f"  [SHUTDOWN] draining durable queues for up to {drain_timeout:.0f}s")
    generation_queue.stop(timeout=drain_timeout, drain=True)
    outbox.stop(timeout=drain_timeout, drain=True)
    if metrics_server:
        metrics_server.shutdown()
    for sig, previous in previous_handlers.items():
        signal.signal(sig, previous)
    print("\n👋 Бот остановлен.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from tg_bot.credentials import secret_from_env_or_credential

    TOKEN = secret_from_env_or_credential(
        "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
    )
    if not TOKEN:
        print("❌ Установите AIOS_TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    run_bot(TOKEN)
