"""
AIOS Telegram Bot — управление агентами через Telegram.

Запуск::
    export AIOS_TELEGRAM_TOKEN="123456:ABC-DEF..."
    python run_telegram_bot.py

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
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

PROJECT_ROOT = Path(__file__).resolve().parent

# === Inventory by photo v22.1 helpers ===
import random as _rnd

from tg_bot.inventory_photos import (  # noqa: E402
    _generate_draft_id, _build_inventory_keyboard, _process_expired_albums,
    _create_inventory_draft_and_ask_confirmation,
)


from tg_bot.common import _safe, _esc_tg, _run_account_control  # noqa: E402
from tg_bot.callbacks import _handle_callback, _handle_button  # noqa: E402
from tg_bot.llm import _llm_chat, _cmd_skills, _cmd_llm_mode, _cmd_console, _llm_status  # noqa: E402
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


from tg_bot.api import TelegramAPI  # noqa: E402


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


TEMPLATES_FILE = PROJECT_ROOT / "data" / "templates.json"
REMINDERS_FILE = PROJECT_ROOT / "data" / "reminders.json"


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
    from tg_bot.inbox_router import _handle_unified_inbox_intent as _f
    return _f(api, chat_id, text)


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
    raw = os.environ.get("TELEGRAM_CHAT_ID", "")
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
    offset = 0

    print("🤖 AIOS Telegram Bot запущен (v10.0 with inline menu)")
    print("   Ожидание сообщений...\n")

    _last_reminder_check = 0.0
    _last_inbox_check = 0.0

    while True:
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
                offset = upd["update_id"] + 1

                # Handle callback queries (button presses) — always process even when paused
                if "callback_query" in upd:
                    callback_chat = upd.get("callback_query", {}).get("message", {}).get("chat", {}).get("id")
                    if not _is_authorized_chat(callback_chat):
                        print(f"  [SECURITY] ignored callback from unauthorized chat {callback_chat}")
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
                print(f"📩 [TG INCOMING] chat={chat_id} ({first_name}): '{text}'")
                if not _is_authorized_chat(chat_id):
                    print(f"  [SECURITY] ignored message from unauthorized chat {chat_id}")
                    try:
                        api.send_message(chat_id, f"⛔ Доступ к AIOS боту ограничен.\nВаш chat_id: `{chat_id}`.\nДобавьте этот ID в `.env` (`TELEGRAM_CHAT_ID={chat_id}`).", parse_mode="Markdown")
                    except Exception:
                        pass
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
                            llm_reply = _llm_chat(chat_id, transcript)
                            if llm_reply:
                                try:
                                    api.send_message(chat_id, llm_reply[:3900])
                                except Exception:
                                    try:
                                        api.send_message(chat_id, llm_reply[:3900], parse_mode="")
                                    except Exception:
                                        pass
                        print(f"  [VOICE] transcript: {transcript[:80]}")
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
                        print(f"  → action {action} (chat {chat_id})")
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
                        print(f"  -> button {btn_action} (chat {chat_id})")
                        continue

                    # Natural language control of Google / Instagram accounts
                    try:
                        from tg_bot.calls import _handle_calls_intent
                        if _handle_calls_intent(api, chat_id, text):
                            print(f"  -> calls-intent handled (chat {chat_id})")
                            continue
                        if _handle_account_intent(api, chat_id, text):
                            print(f"  -> account-intent handled (chat {chat_id})")
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

                    # Regular chat message — send to LLM
                    llm_reply = _llm_chat(chat_id, text)
                    print(f"  [LLM] reply ({len(llm_reply or '')} chars): {(llm_reply or '')[:100]}")
                    if llm_reply:
                        # Remove any remaining cmd tags
                        import re as _re2
                        llm_reply = _re2.sub(r'<cmd>.*?</cmd>', '', llm_reply, flags=_re2.DOTALL)
                        llm_reply = _re2.sub(r'```cmd\n.*?```', '', llm_reply, flags=_re2.DOTALL).strip()
                        # Escape HTML but preserve code blocks
                        llm_reply = llm_reply.replace("&", "&amp;")
                        try:
                            api.send_message(chat_id, llm_reply[:3900])
                            print(f"  -> LLM sent (chat {chat_id})")
                        except Exception as send_err:
                            # Retry without parse_mode
                            try:
                                api.send_message(chat_id, llm_reply[:3900], parse_mode='')
                                print(f"  -> LLM sent plain (chat {chat_id})")
                            except Exception as e2:
                                print(f"  [ERR] send failed: {e2}")
                        # голосовой ответ, если включён
                        if _voice_enabled(chat_id):
                            _send_voice_reply(api, chat_id, llm_reply[:1500])
                    continue

                reply = None
                keyboard = None

                if cmd == "/start" or cmd == "/menu":
                    reply = cmd_start(first_name)
                    keyboard = MAIN_MENU_INLINE
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
                    print(f"  → ответил на {cmd} (chat {chat_id})")

        except KeyboardInterrupt:
            print("\n👋 Бот остановлен.")
            break
        except Exception as exc:
            if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
                continue  # normal for long polling
            print(f"⚠️ Ошибка polling: {exc}")
            time.sleep(3)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TOKEN = os.environ.get("AIOS_TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("❌ Установите AIOS_TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    run_bot(TOKEN)
