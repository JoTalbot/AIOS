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

PROJECT_ROOT = Path(__file__).resolve().parent

# === Inventory by photo v22.1 helpers ===
import random as _rnd

def _generate_draft_id(chat_id: int) -> str:
    return f"{chat_id}_{int(time.time()*1000)}_{_rnd.randint(1000,9999)}"

def _build_inventory_keyboard(draft_id: str, price, photos_len: int):
    try:
        price_int = int(float(price))
        price_label = f"{price_int} грн" if float(price).is_integer() else f"{price} грн"
    except:
        price_label = f"{price} грн"
    return {
        "inline_keyboard": [
            [
                {"text": f"✅ Подтвердить {price_label}", "callback_data": f"inv_confirm_{draft_id}"},
                {"text": "❌ Отмена", "callback_data": f"inv_cancel_{draft_id}"}
            ],
            [
                {"text": f"✅+📢 Склад+OLX ({price_label})", "callback_data": f"inv_confirm_olx_{draft_id}"},
                {"text": f"📢 Только OLX", "callback_data": f"inv_olx_{draft_id}"}
            ],
            [
                {"text": "✏️ Цена", "callback_data": f"inv_edit_price_{draft_id}"},
                {"text": "✏️ Название", "callback_data": f"inv_edit_name_{draft_id}"},
                {"text": "✏️ Кол-во", "callback_data": f"inv_edit_qty_{draft_id}"}
            ],
            [
                {"text": f"📸 +фото ({photos_len} шт)", "callback_data": f"inv_add_photo_{draft_id}"},
                {"text": "🏷 Категория", "callback_data": f"inv_edit_category_{draft_id}"}
            ]
        ]
    }

def _process_expired_albums(api):
    """Обработать альбомы Telegram, которые уже полностью пришли (>2.5 сек без новых фото)."""
    try:
        now = time.time()
        to_process = []
        for mg_id, album in list(_photo_albums.items()):
            if album.get("processed"):
                continue
            if now - album.get("ts", 0) > 2.5:
                to_process.append((mg_id, album))
        for mg_id, album in to_process:
            if len(album.get("photos", [])) == 0:
                _photo_albums.pop(mg_id, None)
                continue
            album["processed"] = True
            chat_id = album.get("chat_id")
            photos = album.get("photos", [])
            caption = album.get("caption") or ""
            # если этот альбом был для добавления фото к существующему черновику
            if chat_id in _pending_add_photo:
                draft_id = _pending_add_photo.get(chat_id)
                draft = _inventory_drafts.get(draft_id)
                if draft:
                    # добавляем фото к черновику
                    for p in photos:
                        if p not in draft["photos"]:
                            draft["photos"].append(p)
                    _last_photo[chat_id] = photos[-1]
                    api.send_message(chat_id,
                        f"📸 Добавил {len(photos)} фото к черновику «{draft.get('name')[:40]}» (теперь {len(draft['photos'])} шт).\nОтправьте ещё или нажмите ✅ Подтвердить.",
                        reply_markup=_build_inventory_keyboard(draft_id, draft.get('price',0), len(draft['photos'])))
                    _photo_albums.pop(mg_id, None)
                    continue
            # иначе создаём новый черновик из альбома
            _create_inventory_draft_and_ask_confirmation(api, chat_id, photos, caption)
            _photo_albums.pop(mg_id, None)
    except Exception as e:
        print(f"  [ALBUM PROCESS ERR] {e}")
        import traceback; traceback.print_exc()

def _create_inventory_draft_and_ask_confirmation(api, chat_id: int, photos: list, caption: str):
    """Создать черновик товара из фото(й) и отправить клавиатуру подтверждения."""
    if not photos:
        return
    first_photo = photos[0]
    # --- Vision ---
    recog = {"status":"error"}
    try:
        import subprocess as _sp2
        r = _sp2.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_photo_recognition.py"), first_photo],
                     capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        out = (r.stdout or "").strip()
        for line in reversed(out.splitlines()):
            if "{" in line and "}" in line:
                try:
                    import json as _js
                    recog = _js.loads(line[line.find("{"):line.rfind("}")+1])
                    break
                except:
                    continue
        if recog.get("status")!="ok":
            try:
                import json as _js
                recog = _js.loads(out.splitlines()[-1])
            except:
                pass
    except Exception as e:
        recog = {"status":"error","error":str(e)}

    part_name = ""
    price_rec = 0
    condition = ""
    compatible = ""
    notes = ""
    provider = recog.get("provider","?")
    if recog.get("status")=="ok":
        part_name = (recog.get("part") or "").strip()
        try:
            price_rec = float(recog.get("price") or 0)
        except:
            price_rec = 0
        condition = recog.get("condition") or ""
        compatible = recog.get("compatible") or ""
        notes = recog.get("notes") or ""

    if caption:
        cap_clean = re.sub(r"^(добавь( на склад)?|создай товар|товар на склад|деталь|запчасть)\s*:?\s*", "", caption, flags=re.IGNORECASE).strip()
        if len(cap_clean)>=2:
            if not part_name or len(cap_clean) > len(part_name):
                part_name = cap_clean
            elif cap_clean.lower() not in part_name.lower():
                part_name = f"{part_name} {cap_clean}".strip()

    if not part_name:
        part_name = caption or "Автозапчасть с фото"

    qty = 1
    price = price_rec
    text_for_parse = caption or ""
    m_qty = re.search(r"(\d+)\s*шт", text_for_parse, re.IGNORECASE)
    if m_qty:
        try:
            qty = max(1, int(m_qty.group(1)))
        except:
            qty = 1
    m_price = re.search(r"(\d[\d\s.,]*)\s*(грн|uah|₴)", text_for_parse, re.IGNORECASE)
    if m_price:
        try:
            price = float(m_price.group(1).replace(" ","").replace(",","."))
        except:
            pass
    else:
        m_price2 = re.search(r"\b(\d{3,6})\b\s*$", text_for_parse)
        if m_price2 and price_rec==0:
            try:
                v=int(m_price2.group(1))
                if 100 <= v <= 50000:
                    price = float(v)
            except:
                pass

    category = "общее"
    try:
        from tg_bot.accounts import _llm_chat_direct as _llm_direct
        cat_prompt = f"Деталь: «{part_name}». Определи категорию из списка (двигатель, кузов, оптика, подвеска, тормоза, электрика, салон, трансмиссия, расходники, система охлаждения, другое) и верни ТОЛЬКО JSON {{\"category\":\"...\"}}."
        cat_resp = _llm_direct(cat_prompt)
        start = cat_resp.find("{")
        end = cat_resp.rfind("}")+1
        if start>=0 and end>start:
            import json as _js
            cj = _js.loads(cat_resp[start:end])
            category = (cj.get("category") or "общее").strip()[:40]
    except Exception:
        low = part_name.lower()
        if any(w in low for w in ("фара","фонарь","оптика","лампа","поворотник")):
            category="оптика"
        elif any(w in low for w in ("радиатор","охлаждение","термостат")):
            category="Система охлаждения"
        elif any(w in low for w in ("рессора","пружина","аморт","подвеска","рычаг","сайлент")):
            category="Подвеска"
        elif any(w in low for w in ("генератор","стартер","проводка","датчик")):
            category="Электрооборудование"
        elif any(w in low for w in ("бампер","капот","крыло","дверь","кузов")):
            category="Кузов"
        elif any(w in low for w in ("тормоз","колодка","диск тормоз")):
            category="Тормоза"
        elif any(w in low for w in ("кпп","коробка","трансмиссия")):
            category="Трансмиссия"

    draft_id = _generate_draft_id(chat_id)
    draft = {
        "draft_id": draft_id,
        "name": part_name[:120],
        "qty": qty,
        "price": price or 0,
        "category": category,
        "photos": photos,
        "condition": condition,
        "compatible": compatible,
        "notes": notes,
        "provider": provider,
        "caption": caption,
        "chat_id": chat_id,
        "ts": time.time(),
    }
    _inventory_drafts[draft_id] = draft

    kb = _build_inventory_keyboard(draft_id, draft["price"], len(photos))

    lines = [
        f"🔍 <b>Черновик товара (vision: {provider})</b>",
        f"📦 <b>{_esc_tg(draft['name'])}</b>",
        f"🔢 Кол-во: {qty} шт",
        f"💰 Цена: {int(price) if float(price).is_integer() else price} грн" + (f" (AI оценил {int(price_rec)} грн)" if price_rec and abs(float(price)-float(price_rec))>1 else ""),
        f"🏷 Категория: {_esc_tg(category)}",
    ]
    if condition:
        lines.append(f"📋 Состояние: {_esc_tg(condition)}")
    if compatible:
        lines.append(f"🚗 Совместимость: {_esc_tg(compatible)}")
    if notes:
        lines.append(f"📝 {_esc_tg(notes)}")
    lines.append(f"📸 Фото: {len(photos)} шт.")
    lines.append("")
    lines.append("Подтвердите или отредактируйте:")

    api.send_message(chat_id, "\n".join(lines), reply_markup=kb)

# === end helpers ===




sys.path.insert(0, str(PROJECT_ROOT))

# ── v20.5 Hygiene: модули вынесены в tg_bot/ (имена импортируются обратно) ──
from tg_bot.common import _safe, _esc_tg, _smart_model, _local_api_json, _run_account_control
from tg_bot.state import _pending_confirm, _last_inbox, _last_inbox_filters, _CHANNELS
from tg_bot.accounts import (
    _fmt_gmail_list, _acct_send_result, _run_acct_cmd, _acct_google, _acct_instagram,
    _llm_extract_json, _llm_extract_gmail, _llm_extract_calendar, _handle_account_intent,
    cmd_accounts, cmd_google, cmd_instagram,
)
from tg_bot.state import _last_photo, _photo_pending, _last_gen_ad, _last_video, _last_gmail_ids, _photo_albums, _inventory_drafts, _pending_inventory_edits, _pending_add_photo
from tg_bot.state import _pending_actions, _pending_confirmations
from tg_bot.treasury import _handle_treasury_intent
from tg_bot.keyboards import (
    MAIN_MENU_KEYBOARD, MAIN_MENU_INLINE, CODER_MENU_KEYBOARD, OLX_MENU_KEYBOARD, ACCOUNTS_MENU_KEYBOARD,
    PHONE_MENU_KEYBOARD, GOOGLE_MENU_KEYBOARD, INSTAGRAM_MENU_KEYBOARD, BOT_MENU_KEYBOARD,
    DANGEROUS_CALLBACKS,
)
from tg_bot.callbacks import (
    _handle_button, _handle_button_inner, _handle_inbox_callback, _handle_olx_send_callback,
    _handle_autonomy_callback, _handle_viber_draft_callback, _handle_signal_draft_callback, _handle_callback,
)
from tg_bot.llm import (
    _chat_history, MAX_HISTORY, _llm_status, _cmd_llm_mode, _cmd_skills, _cmd_console, _llm_chat,
)
from tg_bot.phone import (
    _PHONE_BRAIN_API, _phone_brain_gateway_run, _android_gateway_run, _phone_brain_api_request,
    _handle_phone_brain_intent, _handle_phone_workflow_readiness_intent, _handle_phone_jobs_intent,
    _handle_phone_inventory_intent, _handle_phone_metrics_intent, _handle_phone_bank_monitor_intent,
    _handle_phone_recovery_intent, _handle_phone_weekly_report_intent, _handle_phone_control_center_intent,
    _handle_phone_audit_intent, _phone_lead_queue, _followup_templates, _handle_phone_lead_intent,
    _phone_adapter, _phone_error, _mask_android_notification, _send_phone_status,
    _uklon_route_field_allowed, _uklon_route_field_label, _uklon_next_route_field,
    _parse_uklon_route_request, _handle_android_phone_workflow_intent,
    _cancel_phone_pending, _confirm_phone_pending, _handle_android_gateway_intent,
)
from tg_bot.voice import VOICE_REPLY_FILE, _voice_enabled, _set_voice_enabled, _send_voice_reply, _transcribe_audio
from tg_bot.inbox import (
    INBOX_SCHEDULE_FILE, INBOX_CACHE_FILE, _inbox_cache_load, _inbox_cache_save,
    _inbox_refresh_now, _is_service_preview, _parse_inbox_filters, _collect_inbox,
    _format_inbox, _inbox_keyboard, _inbox_summarize, _llm_chat_direct, _inbox_reply,
    _inbox_voice, _inbox_search, _inbox_mark_read, _inbox_schedule_cmd, _run_due_inbox,
)



_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _value = _line.partition("=")
        _key = _key.strip()
        _value = _value.strip().strip('\"').strip("'")
        if _key and _key not in os.environ:
            os.environ[_key] = _value

# ---------------------------------------------------------------------------
# Telegram API helpers (zero-dependency)
# ---------------------------------------------------------------------------


class TelegramAPI:
    """Minimal Telegram Bot API client (polling mode)."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._base = f"https://api.telegram.org/bot{token}"

    def _request(self, method: str, data: dict | None = None) -> dict:
        url = f"{self._base}/{method}"
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read())

    def get_updates(self, offset: int = 0) -> list[dict]:
        result = self._request("getUpdates", {"offset": offset, "timeout": 30})
        return result.get("result", [])

    def send_message(
        self, chat_id: int, text: str, parse_mode: str = "HTML", disable_web_page_preview: bool = True,
        reply_markup: dict | None = None,
    ) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": text[:4000],
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            return self._request("sendMessage", payload)
        except urllib.error.HTTPError as e:
            # Telegram 400 Bad Request: невалидный HTML (raw <...>) — повторяем как plain text
            if e.code == 400 and parse_mode == "HTML":
                payload["parse_mode"] = ""
                return self._request("sendMessage", payload)
            raise

    def answer_callback(self, callback_query_id: str, text: str = "") -> dict:
        return self._request("answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": text[:200],
        })

    def edit_message(self, chat_id: int, message_id: int, text: str,
                     parse_mode: str = "HTML", reply_markup: dict | None = None) -> dict:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text[:4000],
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            return self._request("editMessageText", payload)
        except urllib.error.HTTPError as e:
            if e.code == 400 and parse_mode == "HTML":
                payload["parse_mode"] = ""
                return self._request("editMessageText", payload)
            raise

    def get_file(self, file_id: str) -> dict:
        """Получить информацию о файле (file_path) по file_id."""
        return self._request("getFile", {"file_id": file_id}).get("result", {})

    def download_file_by_id(self, file_id: str, dest: str | None = None) -> str:
        """Скачать файл (фото и т.п.) по file_id в локальный путь; вернуть путь."""
        info = self.get_file(file_id)
        path = info.get("file_path", "")
        if not path:
            raise ValueError(f"Нет file_path для file_id {file_id}")
        url = f"https://api.telegram.org/file/bot{self._token}/{path}"
        with urllib.request.urlopen(url, timeout=90) as resp:
            data = resp.read()
        if not dest:
            ext = Path(path).suffix or ".jpg"
            dest = f"/tmp/aios_tg_{int(time.time() * 1000)}{ext}"
        Path(dest).write_bytes(data)
        return dest

    def _multipart(self, method: str, chat_id: int, field: str, file_path: str,
                   caption: str = "") -> dict:
        """Универсальная отправка файла (photo/document)."""
        import mimetypes
        boundary = "----aios" + str(int(time.time() * 1000))
        content = Path(file_path).read_bytes()

        def _field(name: str, value: str) -> bytes:
            return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                    f"{value}\r\n").encode()

        fn = Path(file_path).name
        ct = mimetypes.guess_type(fn)[0] or "application/octet-stream"
        body = b"".join([
            _field("chat_id", str(chat_id)),
            _field("caption", caption[:1000]) if caption else b"",
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{fn}\"\r\n"
             f"Content-Type: {ct}\r\n\r\n").encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(
            f"{self._base}/{method}", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())

    def send_photo(self, chat_id: int, photo_path: str, caption: str = "") -> dict:
        return self._multipart("sendPhoto", chat_id, "photo", photo_path, caption)

    def send_document(self, chat_id: int, file_path: str, caption: str = "") -> dict:
        return self._multipart("sendDocument", chat_id, "document", file_path, caption)

    def send_voice(self, chat_id: int, voice_path: str, caption: str = "") -> dict:
        return self._multipart("sendVoice", chat_id, "voice", voice_path, caption)


# ---------------------------------------------------------------------------
# Command handlers — каждая возвращает строку для отправки в чат
# ---------------------------------------------------------------------------






@_safe
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
        "  /stats — статистика БД и оркестратора\n"
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
    """Детерминированно обработать статусы продаж без риска LLM-путаницы.

    Эти команды принадлежат владельцу бота. Изменение остатков разрешено
    только после явной фразы владельца («отправил…», «доставлено…») либо
    подтверждённого статуса Новой Почты в таймере.
    """
    raw = str(text or "").strip()
    normalized = " ".join(raw.casefold().split())
    if not normalized:
        return False
    try:
        from aios_core.sales_lifecycle import SalesLifecycle
        lifecycle = SalesLifecycle(PROJECT_ROOT)
    except Exception as exc:
        print(f"  [SALES] init error: {exc}")
        return False

    crm_phrases = ("crm", "сделки", "статус продаж", "воронка продаж", "продажи crm")
    if any(phrase in normalized for phrase in crm_phrases):
        # CRM-команды: экспорт и поиск клиента не требуют LLM и не раскрывают
        # полный номер телефона в Telegram.
        if "экспорт" in normalized or "export" in normalized:
            try:
                from run_crm import export_csv
                from aios_core.crm import CRMStore
                exported = export_csv(CRMStore(PROJECT_ROOT))
                api.send_document(chat_id, exported["file"], caption=f"💼 CRM экспорт · {exported['rows']} клиентов")
            except Exception as exc:
                api.send_message(chat_id, f"⚠️ Не удалось экспортировать CRM: {_esc_tg(str(exc))[:180]}")
            return True
        if "клиент" in normalized or "customers" in normalized:
            query = re.sub(r"^(?:crm\s*)?(?:клиенты|клиент|customers?)\s*:?\s*", "", raw, flags=re.IGNORECASE).strip()
            try:
                from aios_core.crm import CRMStore
                store = CRMStore(PROJECT_ROOT)
                if query:
                    customer = store.find(query)
                    customers = [customer] if customer else []
                else:
                    customers = store.snapshot(limit=12).get("customers", [])
                if not customers:
                    api.send_message(chat_id, "👥 CRM: клиентов по запросу не найдено.")
                    return True
                lines = ["👥 <b>Клиенты CRM</b>"]
                for customer in customers[:12]:
                    tags = " · ".join(customer.get("tags") or []) or "без тега"
                    lines.append(
                        f"• <b>{_esc_tg(customer.get('display_name'))}</b> {customer.get('phone_masked') or ''}\n"
                        f"  {customer.get('sales_count', 0)} сделок · {customer.get('lifetime_amount', 0):.0f} грн · {tags}\n"
                        f"  Последнее: {_esc_tg(customer.get('last_item') or '—')} · {_esc_tg(customer.get('last_status') or '—')}")
                api.send_message(chat_id, "\n".join(lines)[:3900])
            except Exception as exc:
                api.send_message(chat_id, f"⚠️ CRM временно недоступна: {_esc_tg(str(exc))[:180]}")
            return True

        crm = lifecycle.crm_snapshot()
        status_label = {
            "awaiting_shipment": "⏳ ждёт отправки", "ttn_created": "⏳ ТТН создана",
            "in_transit": "🚚 в пути", "delivered": "✅ доставлено",
            "returning": "↩️ возврат в пути", "returned": "↩️ возврат",
            "return_received": "📦 возвращено на склад",
        }
        lines = [
            "💼 <b>Продажи и CRM</b>",
            "━━━━━━━━━━━━━━━━",
            f"Активные: <b>{crm['active']}</b> · ждут отправки: <b>{crm['awaiting']}</b> · в пути: <b>{crm['in_transit']}</b>",
            f"Доставлено: <b>{crm['delivered']}</b> · возвраты: <b>{crm['returned']}</b> · открытые задачи: <b>{crm['open_tasks']}</b>",
            f"Сумма активных сделок: <b>{crm['pipeline_amount']:.0f} грн</b>",
        ]
        recent = crm.get("sales") or []
        if recent:
            lines.append("━━━━━━━━━━━━━━━━")
            lines.append("<b>Последние сделки</b>")
            for sale in recent[:8]:
                task = " · 📌 задача" if sale.get("task_open") else ""
                lines.append(
                    f"• {status_label.get(sale.get('status'), sale.get('status'))} · "
                    f"<b>{_esc_tg(sale.get('item'))[:70]}</b> · ТТН <code>{_esc_tg(sale.get('ttn') or '—')}</code> · "
                    f"{float(sale.get('amount') or 0):.0f} грн{task}")
        lines.append("━━━━━━━━━━━━━━━━")
        lines.append("<i>«задачи отправки» · «отправил &lt;ТТН&gt;» · «доставлено &lt;ТТН&gt;»</i>")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    task_phrases = (
        "задачи отправки", "задачи по отправке", "что нужно отправить",
        "что отправить", "ожидает отправки", "задачи продаж",
    )
    if any(phrase in normalized for phrase in task_phrases):
        rows = lifecycle.list_open_tasks()
        if not rows:
            api.send_message(chat_id, "📋 Открытых задач по отправкам и возвратам нет.")
            return True
        lines = ["📋 <b>Задачи по продажам:</b>"]
        for row in rows[:15]:
            task, sale = row["task"], row["sale"]
            item = _esc_tg(sale.get("item") or "товар")
            ttn = _esc_tg(sale.get("ttn") or "—")
            if task.get("kind") == "return_receive":
                lines.append(f"• ↩️ Принять возврат: <b>{item}</b> · ТТН <code>{ttn}</code>")
            else:
                lines.append(f"• 📦 Отправить: <b>{item}</b> · ТТН <code>{ttn}</code>")
        lines.append("\nПосле передачи: «отправил <ТТН>». После доставки: «доставлено <ТТН>».")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    def _reference(match) -> str:
        value = (match.group(1) or "").strip(" ,.:;—–-") if match.lastindex else ""
        generic = {"этот товар", "эту посылку", "этот", "эту", "товар", "посылку", "посылка",
                   "его", "ее", "цей товар", "цю посилку", "посилку"}
        return "" if value.casefold() in generic else value

    # Важно проверять приём возврата раньше «получил…», иначе фраза
    # «получил возврат» могла бы ошибочно закрыть продажу как доставленную.
    m = re.match(r"^(?:я\s+)?(?:получил(?:а)?\s+возврат|возврат\s+получил(?:а)?|"
                 r"принял(?:а)?\s+возврат|повернув(?:ла)?\s+на\s+склад)\b\s*(.*)$", raw, re.I)
    if m:
        result = lifecycle.mark_return_received(_reference(m), source="telegram")
    else:
        m = re.match(r"^(?:посылка\s+|товар\s+)?(?:вернулась|вернулся|возвращена|возвращен|"
                     r"повернулась|повернувся|повернено|возврат)\b\s*(.*)$", raw, re.I)
        if m:
            result = lifecycle.mark_returned(_reference(m), source="telegram")
        else:
            m = re.match(r"^(?:я\s+)?(?:(?:товар|посылку|посилку)\s+)?(?:уже\s+)?"
                         r"(?:отправил(?:а)?|відправив(?:ла)?|передал(?:а)?\s+(?:в|на)\s+"
                         r"(?:новую\s+почту|нову\s+пошту|нп)|сдал(?:а)?\s+(?:в|на)\s+"
                         r"(?:новую\s+почту|нову\s+пошту|нп))\b\s*(.*)$", raw, re.I)
            if m:
                result = lifecycle.mark_shipped(_reference(m), source="telegram")
            else:
                m = re.match(r"^(?:товар\s+|посылка\s+|посилка\s+)?(?:доставлен(?:а|о|ы)?|"
                             r"доставили|доставлено|клиент\s+получил|клієнт\s+отримав|"
                             r"отримано\s+(?:клієнтом|покупцем))\b\s*(.*)$", raw, re.I)
                if not m:
                    return False
                result = lifecycle.mark_delivered(_reference(m), source="telegram")

    message = str(result.get("message") or result.get("error") or "Не удалось обновить сделку.")
    # SalesLifecycle возвращает обычный текст. Экранируем название товара,
    # если пользователь когда-то добавил в него HTML-символы.
    api.send_message(chat_id, _esc_tg(message)[:3900])
    return True


def _send_unified_inbox(api, chat_id: int, text: str = "", filters: dict | None = None,
                       refresh: bool = False) -> None:
    """Показать инбокс.

    refresh=True — собрать из каналов (дёргает адаптеры) и обновить кэш;
    refresh=False — показать сохранённые сообщения (не дёргая адаптеры).
    Показываются только непрочитанные карточки. Почта — отдельная команда «почта».
    """
    filters = dict(filters or _parse_inbox_filters(text))
    lower = " ".join((text or "").casefold().split())

    # почта вынесена в отдельную команду «почта»
    if filters.get("channels") == ["gmail"] or lower in (
            "инбокс почта", "инбокс гмаил", "инбокс gmail", "инбокс только почта"):
        api.send_message(chat_id, "📬 <b>Почта вынесена в отдельную команду.</b>\n\n"
                                  "Напишите «почта» или «проверь почту» — покажу письма отдельно.")
        return

    if refresh:
        api.send_message(chat_id, "⏳ <b>Обновляю инбокс…</b> проверяю каналы")
        items = _inbox_refresh_now(filters)
        if not items:
            api.send_message(chat_id, "📭 <b>Инбокс пуст</b>\nНовых карточек по каналам нет.",
                             reply_markup=_inbox_keyboard([], force=True))
            return
    else:
        items = _inbox_cache_load()
        if not items:
            api.send_message(chat_id, "📥 <b>Инбокс</b>\n\nСохранённых сообщений пока нет.\n"
                                      "Нажмите «🔄 Обновить», чтобы проверить каналы.",
                             reply_markup=_inbox_keyboard([], force=True))
            return

    # показываем только непрочитанные
    unread_items = [it for it in items if it.get("unread")]
    if not unread_items:
        api.send_message(chat_id, "✅ <b>Инбокс</b>\nНовых непрочитанных сообщений нет.",
                         reply_markup=_inbox_keyboard([], force=True))
        return
    _last_inbox[chat_id] = unread_items
    _last_inbox_filters[chat_id] = filters
    if any(word in lower for word in ("сводк", "резюме", "кратко", "умн")):
        api.send_message(chat_id, "🧠 Составляю сводку по карточкам…")
        api.send_message(chat_id, _inbox_summarize(unread_items)[:3900])
    else:
        api.send_message(chat_id, _format_inbox(unread_items, filters),
                         reply_markup=_inbox_keyboard(unread_items))


def _handle_unified_inbox_intent(api, chat_id: int, text: str) -> bool:
    """Приоритетный роутер инбокса до Instagram Direct и прочих платформ."""
    t = " ".join((text or "").casefold().split())
    if not t:
        return False

    # Расписание должно перехватываться раньше общего слова «инбокс».
    if re.match(r"^(присылай|пришли|включи|отключи|выключи|убери)\s+инбокс", t) or \
       re.match(r"^(включи|отключи)\s+расписание\s+инбокса", t):
        _inbox_schedule_cmd(api, chat_id, text)
        return True

    # Пользовательский вариант «отметить все непрочитанные сообщения в инбоксе
    # прочитанными» раньше ошибочно попадал в обработчик Instagram Direct.
    mark_read = ((any(stem in t for stem in ("отмет", "пометь", "отмеч")) and "прочитан" in t
                  and any(word in t for word in ("инбокс", "сообщен", "все", "всё")))
                 or "всё прочитано" in t or "все прочитаны" in t)
    if mark_read:
        _inbox_mark_read(api, chat_id)
        return True

    m_reply = re.match(r"^(ответь|reply|отв[её]ть)\s+(?:на\s+)?#?(\d+)\s*:?\s*(.+)$", text, re.IGNORECASE)
    if m_reply:
        if chat_id not in _last_inbox:
            api.send_message(chat_id, "ℹ️ Сначала откройте «инбокс», затем выберите номер карточки.")
            return True
        idx = int(m_reply.group(2))
        body = m_reply.group(3).strip()
        items = _last_inbox.get(chat_id, [])
        if 1 <= idx <= len(items):
            _inbox_reply(api, chat_id, items[idx - 1], body)
        else:
            api.send_message(chat_id, f"❌ Нет карточки №{idx} в последнем инбоксе.")
        return True

    if any(phrase in t for phrase in ("озвучь инбокс", "озвучь всё", "голосом инбокс", "прочитай инбокс вслух")):
        api.send_message(chat_id, "⏳ Собираю карточки для озвучки…")
        items, _summary = _collect_inbox({})
        if not items:
            api.send_message(chat_id, "📭 Инбокс пуст.")
        else:
            _last_inbox[chat_id] = items
            _last_inbox_filters[chat_id] = {}
            _inbox_voice(api, chat_id, items)
        return True

    m_search = re.match(r"^(найди во всех|ищи везде|найди везде|поиск по всем)\s*(?:чатах|сообщениях|каналах)?\s*:?\s*(.+)$", text, re.IGNORECASE)
    if m_search:
        query = m_search.group(2).strip()
        if query:
            api.send_message(chat_id, f"🔍 Ищу «{_esc_tg(query)}» по подключённым каналам…")
            _inbox_search(api, chat_id, query)
        else:
            api.send_message(chat_id, "🔍 Формат: «найди во всех чатах &lt;запрос&gt;»")
        return True

    inbox_terms = ("инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений", "где что новое", "проверь всё")
    if any(term in t for term in inbox_terms):
        _send_unified_inbox(api, chat_id, text, refresh=True)
        return True
    return False


# Мини-кэш доступности Phone Brain: если демон недавно не отвечал — сразу
# уходим в legacy subprocess, не задерживая обработку сообщения.






# Последние показанные безопасные карточки потенциальных лидов: chat_id -> rows.
# Последние показанные metadata-only CRM follow-up задачи телефона.
# Последние показанные metadata-only задачи банковских уведомлений.







def _handle_freelance_intent(api, chat_id: int, text: str) -> bool:
    """Обрабатывает фриланс-команды владельца.
    Команды:
      «подтверди фриланс <task_id>» или «confirm freelance <task_id>» — подтверждает оплату за выполненную задачу и зачисляет деньги в 4 кошелька.
      «список фриланса» или «фриланс список» — выводит список решенных задач, ожидающих подтверждения оплаты.
      «инвойс фриланс <task_id>» или «invoice freelance <task_id>» — генерирует и отправляет интерактивный HTML-инвойс для этой задачи.
    """
    import re as _re3
    t = " ".join(str(text or "").casefold().split())

    # 1. Обработка подтверждения оплаты
    approve = _re3.match(r"^(?:подтверди\s+фриланс|подтвердить\s+фриланс|confirm\s+freelance)\s+(\S+)", t)
    if approve:
        task_id = approve.group(1).strip()
        tasks_file = PROJECT_ROOT / "data" / "freelance_tasks.json"
        if not tasks_file.exists():
            api.send_message(chat_id, "⚠️ Файл задач фриланса не найден.")
            return True

        try:
            tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        except Exception as e:
            api.send_message(chat_id, f"⚠️ Ошибка чтения файла задач: {e}")
            return True

        target_task = None
        for task in tasks:
            if task.get("id") == task_id:
                target_task = task
                break

        if not target_task:
            api.send_message(chat_id, f"❌ Задача с ID <code>{task_id}</code> не найдена.")
            return True

        if target_task.get("status") == "PAID":
            api.send_message(chat_id, f"ℹ️ Оплата по задаче <code>{task_id}</code> уже была зачислена ранее.")
            return True

        # Зачисляем реальный доход в кошелек системы
        from aios_core.crypto_wallet import AIOSWalletManager
        wallet = AIOSWalletManager(str(PROJECT_ROOT / "data"))

        try:
            budget = float(target_task.get("budget_usd", 0.0))
            source = f"Freelance:{target_task.get('source', 'unknown')}"

            # Начисляем и делим на 4 кошелька
            wallet.record_income(
                amount_usd=budget,
                source=source,
                task_id=task_id
            )

            # Меняем статус на PAID
            target_task["status"] = "PAID"
            tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

            # Составляем сообщение без f-string с literal newlines
            txt = "✅ <b>Оплата фриланса зачислена!</b>\\n\\n"
            txt += "ID: <code>" + task_id + "</code>\\n"
            txt += "Задача: <i>" + str(target_task.get('title', '')) + "</i>\\n"
            txt += "Сумма: <b>$" + f"{budget:.2f}" + " USD</b>\\n\\n"
            txt += "Бюджет распределен по 25% ($" + f"{budget*0.25:.2f}" + " каждому): Разработчик, Инвестор, Персонал, Система."

            api.send_message(chat_id, txt)
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка при фиксации оплаты: {e}")

        return True

    # 2. Обработка просмотра списка
    if any(phrase in t for phrase in ("список фриланса", "фриланс список", "фриланс задачи", "ожидают оплаты")):
        tasks_file = PROJECT_ROOT / "data" / "freelance_tasks.json"
        if not tasks_file.exists():
            api.send_message(chat_id, "📭 Фриланс-задач нет.")
            return True

        try:
            tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        except Exception:
            api.send_message(chat_id, "⚠️ Ошибка чтения файла задач.")
            return True

        pending = [t for t in tasks if t.get("status") == "BID_SUBMITTED"]
        if not pending:
            api.send_message(chat_id, "📭 Нет фриланс-задач, ожидающих подтверждения оплаты.")
            return True

        lines = [f"📋 <b>Фриланс-задачи в работе (ожидают оплаты): {len(pending)}</b>"]
        for task in pending[-15:]:
            lines.append(
                f"• ID: <code>{task.get('id')}</code>\\n"
                f"  <i>{task.get('title')}</i>\\n"
                f"  Бюджет: <b>${task.get('budget_usd')} USD</b> (Источник: {task.get('source')})\\n"
                f"  Инвойс: <code>инвойс фриланс {task.get('id')}</code>\\n"
                f"  Подтвердить оплату: <code>подтверди фриланс {task.get('id')}</code>"
            )
        api.send_message(chat_id, "\\n\\n".join(lines)[:4000])
        return True

    # 3. Обработка получения инвойса
    get_inv = _re3.match(r"^(?:инвойс\\s+фриланс|invoice\\s+freelance)\\s+(\\S+)\\b", t)
    if get_inv:
        task_id = get_inv.group(1).strip()
        tasks_file = PROJECT_ROOT / "data" / "freelance_tasks.json"
        if not tasks_file.exists():
            api.send_message(chat_id, "⚠️ Файл задач фриланса не найден.")
            return True

        try:
            tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        except Exception:
            api.send_message(chat_id, "⚠️ Ошибка чтения файла задач.")
            return True

        target_task = None
        for task in tasks:
            if task.get("id") == task_id:
                target_task = task
                break

        if not target_task:
            api.send_message(chat_id, f"❌ Задача с ID <code>{task_id}</code> не найдена.")
            return True

        api.send_message(chat_id, "📊 <b>Генерирую интерактивный счет для задачи...</b>")
        from aios_core.invoice_generator import AIOSInvoiceGenerator
        invoicer = AIOSInvoiceGenerator(str(PROJECT_ROOT / "data"))
        try:
            invoice_path = invoicer.generate_invoice_html(
                client_name=target_task.get("source", "unknown"),
                amount_usd=float(target_task.get("budget_usd", 0.0)),
                service_desc=target_task.get("title", ""),
                invoice_id=task_id
            )
            api.send_document(chat_id, invoice_path, caption=f"📑 Инвойс № {task_id} · {target_task.get('source')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка выписки счета: {e}")
        return True

    return False



























































# ---------------------------------------------------------------------------
# Coder commands — MetaCognitiveCoder integration
# ---------------------------------------------------------------------------


_coder_mod = None

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
                if not _is_authorized_chat(chat_id):
                    print(f"  [SECURITY] ignored message from unauthorized chat {chat_id}")
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
                            _ao = globals()["_auto_core"].process_owner(chat_id, text)
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
