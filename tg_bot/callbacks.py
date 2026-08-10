"""Callbacks: inline-кнопки, inbox/olx/autonomy/draft колбэки
(выделено из run_telegram_bot.py)."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from tg_bot.common import PROJECT_ROOT, _esc_tg, _run_account_control
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from run_telegram_bot import TelegramAPI
from tg_bot.accounts import (
    _acct_google, _acct_instagram, _run_acct_cmd, _handle_account_intent, cmd_accounts,
)
from tg_bot.inbox import (
    _collect_inbox, _format_inbox, _inbox_keyboard, _inbox_reply,
    _inbox_summarize, _inbox_voice, _inbox_mark_read, _inbox_search,
)
from tg_bot.keyboards import (
    MAIN_MENU_KEYBOARD, CODER_MENU_KEYBOARD, OLX_MENU_KEYBOARD, ACCOUNTS_MENU_KEYBOARD,
    PHONE_MENU_KEYBOARD, GOOGLE_MENU_KEYBOARD, INSTAGRAM_MENU_KEYBOARD, BOT_MENU_KEYBOARD,
    DANGEROUS_CALLBACKS,
)
from tg_bot.llm import _cmd_llm_mode, _llm_chat
from tg_bot.phone import (
    _cancel_phone_pending, _confirm_phone_pending, _phone_adapter,
    _handle_phone_audit_intent, _handle_phone_bank_monitor_intent,
    _handle_phone_control_center_intent, _handle_phone_inventory_intent,
    _handle_phone_lead_intent, _handle_phone_metrics_intent,
    _handle_phone_recovery_intent, _handle_phone_workflow_readiness_intent,
    _send_phone_status,
)
from tg_bot.state import (
    _pending_confirm, _last_inbox, _last_inbox_filters,
    _last_photo, _last_gen_ad, _last_gmail_ids,
    _last_phone_leads, _phone_brain_state, _CHANNELS,
    _pending_actions, _pending_confirmations,
    _inventory_drafts, _pending_inventory_edits, _pending_add_photo, _photo_albums,
)
from tg_bot.treasury import _handle_treasury_intent
from tg_bot.voice import _send_voice_reply, _set_voice_enabled, _voice_enabled

def _m():
    """Lazy-доступ к монолиту run_telegram_bot (cmd-функции, _paused)."""
    import run_telegram_bot
    return run_telegram_bot




def _handle_inventory_callback(api: TelegramAPI, chat_id: int, cb_id: str, data: str, msg_id: int = 0) -> bool:
    """Обработка инлайн-кнопок для черновиков склада по фото (фича v22.1)."""
    try:
        if data.startswith("inv_confirm_olx_"):
            draft_id = data[len("inv_confirm_olx_"):]
            return _inv_do_confirm_and_olx(api, chat_id, cb_id, draft_id, msg_id)
        elif data.startswith("inv_olx_confirm_"):
            # повторная попытка публикации после генерации
            draft_id = data[len("inv_olx_confirm_"):]
            return _inv_do_create_olx(api, chat_id, cb_id, draft_id, with_inventory=False)
        elif data.startswith("inv_olx_"):
            draft_id = data[len("inv_olx_"):]
            return _inv_do_create_olx(api, chat_id, cb_id, draft_id, with_inventory=False)
        elif data.startswith("inv_confirm_"):
            draft_id = data[len("inv_confirm_"):]
            return _inv_do_confirm(api, chat_id, cb_id, draft_id, msg_id)
        elif data.startswith("inv_cancel_"):
            draft_id = data[len("inv_cancel_"):]
            return _inv_do_cancel(api, chat_id, cb_id, draft_id, msg_id)
        elif data.startswith("inv_edit_price_"):
            draft_id = data[len("inv_edit_price_"):]
            return _inv_do_request_edit(api, chat_id, cb_id, draft_id, "price")
        elif data.startswith("inv_edit_name_"):
            draft_id = data[len("inv_edit_name_"):]
            return _inv_do_request_edit(api, chat_id, cb_id, draft_id, "name")
        elif data.startswith("inv_edit_qty_"):
            draft_id = data[len("inv_edit_qty_"):]
            return _inv_do_request_edit(api, chat_id, cb_id, draft_id, "qty")
        elif data.startswith("inv_edit_category_"):
            draft_id = data[len("inv_edit_category_"):]
            return _inv_do_request_edit(api, chat_id, cb_id, draft_id, "category")
        elif data.startswith("inv_add_photo_"):
            draft_id = data[len("inv_add_photo_"):]
            return _inv_do_request_add_photo(api, chat_id, cb_id, draft_id)
        return False
    except Exception as e:
        print(f"  [INV CB ERR] {data}: {e}")
        import traceback; traceback.print_exc()
        return False


def _inv_do_confirm(api, chat_id, cb_id, draft_id, msg_id=0):
    draft = _inventory_drafts.get(draft_id)
    if not draft:
        try:
            api.answer_callback(cb_id, "❌ Черновик не найден (истёк)")
        except:
            pass
        return True
    if draft.get("chat_id") != chat_id:
        try:
            api.answer_callback(cb_id, "❌ Чужой черновик")
        except:
            pass
        return True
    # создаём товар на складе
    import subprocess as _sp
    from pathlib import Path
    PROJECT_ROOT = Path("/root/AIOS")
    photos = draft.get("photos") or []
    # если есть pending_add_photo и несколько фото добавлено позже — мерджим
    # вызываем run_inventory.py add с мульти-фото
    name = draft.get("name") or "Автозапчасть"
    qty = draft.get("qty") or 1
    price = draft.get("price") or 0
    category = draft.get("category") or "общее"
    # формируем команду — используем photos как запятые, т.к. новая версия поддерживает список через запятую в одном --photo? Лучше через несколько --photo? Упростим: первый идет как --photo, остальные как дополнительные файлы скопируем через _save_photos внутри, но CLI пока поддерживает только один --photo.
    # Поэтому передадим все через запятую, а run_inventory.py теперь понимает запятую.
    photo_arg = ",".join(photos) if photos else ""
    cmd = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"), "add", name, str(qty), str(price), category]
    if photo_arg:
        cmd += ["--photo", photo_arg]
    try:
        r = _sp.run(cmd, capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        out = (r.stdout or "").strip().splitlines()
        last = out[-1] if out else ""
        import json as _json
        if "{" in last:
            res = _json.loads(last[last.find("{"):])
        else:
            res = {"status":"error","error":last[:200]}
    except Exception as e:
        res = {"status":"error","error":str(e)[:200]}

    if res.get("status")=="ok":
        it = res.get("item",{})
        try:
            api.answer_callback(cb_id, f"✅ Создано: {name[:30]}")
        except:
            pass
        try:
            # убираем клавиатуру у сообщения
            api.edit_message(chat_id, msg_id, f"✅ <b>Товар создан на складе!</b>\n📦 <b>{_esc_tg(it.get('name') or name)}</b>\n🔢 {it.get('qty')} шт · 💰 {it.get('price')} грн\n🏷 {it.get('category')}\n📸 Фото: {len(it.get('photos') or [it.get('photo')])} шт", parse_mode="HTML")
        except:
            pass
        api.send_message(chat_id,
            f"✅ <b>Товар создан!</b>\n📦 <b>{_esc_tg(it.get('name') or name)}</b>\n🔢 {it.get('qty')} шт · 💰 {it.get('price')} грн\n"
            f"🏷 {_esc_tg(it.get('category') or category)}\n"
            f"📸 Фото: {len(it.get('photos') or [it.get('photo') or '—'])} шт\n\n"
            f"Команды: «найди деталь { _esc_tg(name[:25]) }» · «создай объявление: { _esc_tg(name[:35]) }»")
        # удаляем черновик
        _inventory_drafts.pop(draft_id, None)
        _pending_add_photo.pop(chat_id, None)
    else:
        try:
            api.answer_callback(cb_id, "❌ Ошибка")
        except:
            pass
        api.send_message(chat_id, f"❌ Не удалось создать товар: {_esc_tg(res.get('error','?'))}")
    return True


def _inv_do_cancel(api, chat_id, cb_id, draft_id, msg_id=0):
    draft = _inventory_drafts.pop(draft_id, None)
    _pending_add_photo.pop(chat_id, None)
    try:
        api.answer_callback(cb_id, "❌ Отменено")
    except:
        pass
    try:
        api.edit_message(chat_id, msg_id, f"❌ <b>Черновик отменён</b>\n<i>{_esc_tg(draft.get('name')[:60] if draft else '')}</i>", parse_mode="HTML")
    except:
        api.send_message(chat_id, "❌ Черновик отменён.")
    return True


def _inv_do_request_edit(api, chat_id, cb_id, draft_id, field):
    draft = _inventory_drafts.get(draft_id)
    if not draft:
        try:
            api.answer_callback(cb_id, "❌ Черновик не найден")
        except:
            pass
        return True
    # помечаем ожидание редактирования
    _pending_inventory_edits[chat_id] = {"draft_id": draft_id, "field": field}
    try:
        api.answer_callback(cb_id, f"✏️ Введите новое значение: {field}")
    except:
        pass
    prompts = {
        "price": "💰 Введите новую цену в грн (число), например: 1500",
        "name": "📦 Введите новое название детали, например: Фара BMW X5 ксенон",
        "qty": "🔢 Введите количество (число), например: 2",
        "category": "🏷 Введите категорию: оптика, кузов, подвеска, тормоза, электрика, система охлаждения, трансмиссия, другое"
    }
    api.send_message(chat_id, prompts.get(field, f"✏️ Введите новое значение для {field}:"))
    return True


def _inv_do_request_add_photo(api, chat_id, cb_id, draft_id):
    draft = _inventory_drafts.get(draft_id)
    if not draft:
        try:
            api.answer_callback(cb_id, "❌ Черновик не найден")
        except:
            pass
        return True
    _pending_add_photo[chat_id] = draft_id
    try:
        api.answer_callback(cb_id, "📸 Пришлите ещё фото")
    except:
        pass
    api.send_message(chat_id, "📸 Пришлите дополнительное фото для этого товара (как фото, не как файл).\nЯ добавлю его к галерее черновика.")
    return True





def _inv_do_create_olx(api, chat_id, cb_id, draft_id, with_inventory=False):
    """Создать объявление OLX из черновика (опционально сначала создать на складе)."""
    draft = _inventory_drafts.get(draft_id)
    if not draft:
        try:
            api.answer_callback(cb_id, "❌ Черновик не найден")
        except:
            pass
        return True
    if draft.get("chat_id") != chat_id:
        try:
            api.answer_callback(cb_id, "❌ Чужой черновик")
        except:
            pass
        return True

    try:
        api.answer_callback(cb_id, "📢 Создаю OLX...")
    except:
        pass

    # ШАГ 1: если нужно, сначала создаём на складе
    if with_inventory:
        # вызываем логику confirm (но без повторного удаления черновика сразу)
        import subprocess as _sp
        from pathlib import Path
        PROJECT_ROOT = Path("/root/AIOS")
        photos = draft.get("photos") or []
        name = draft.get("name") or "Автозапчасть"
        qty = draft.get("qty") or 1
        price = draft.get("price") or 0
        category = draft.get("category") or "общее"
        photo_arg = ",".join(photos) if photos else ""
        cmd = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"), "add", name, str(qty), str(price), category]
        if photo_arg:
            cmd += ["--photo", photo_arg]
        try:
            r = _sp.run(cmd, capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        except Exception as e:
            api.send_message(chat_id, f"⚠️ Не удалось создать на складе: {e}, но продолжу с OLX...")

    # ШАГ 2: создаём объявление OLX
    import subprocess as _sp2
    from pathlib import Path
    PROJECT_ROOT = Path("/root/AIOS")
    photos = draft.get("photos") or []
    name = draft.get("name") or "Автозапчасть"
    # Формируем строку для генератора объявления: название + цена + состояние
    part_desc = name
    if draft.get("condition"):
        part_desc += f", {draft['condition']}"
    if draft.get("compatible"):
        part_desc += f", совместим с {draft['compatible']}"
    # Берём первое фото для OLX (пока OWL адаптер поддерживает 1, но передадим все через запятую — мы обновим run_olx_ad_gen)
    photo_arg = photos[0] if photos else ""
    all_photos_arg = ",".join(photos) if photos else ""

    api.send_message(chat_id, f"⏳ Генерирую объявление OLX для «{_esc_tg(name[:60])}» с {len(photos)} фото... ~30-60 сек (Chrome Twin)")

    try:
        # Генерация + публикация
        cmd = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "create", part_desc, "--confirm"]
        if all_photos_arg:
            cmd += ["--photo", all_photos_arg]
        r = _sp2.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(PROJECT_ROOT))
        out = (r.stdout or "").strip()
        # ищем последний JSON
        import json as _js
        res = {"status":"error","error":"пустой ответ"}
        for line in reversed(out.splitlines()):
            if "{" in line and "}" in line:
                try:
                    res = _js.loads(line[line.find("{"):line.rfind("}")+1])
                    break
                except:
                    continue
    except Exception as e:
        res = {"status":"error","error":str(e)}

    if res.get("status") in ("published","ok","draft_created","need_confirm"):
        if res.get("status") == "published":
            api.send_message(chat_id,
                f"✅ <b>Опубликовано на OLX!</b>\n"
                f"📦 <b>{_esc_tg(name)}</b>\n"
                f"💰 {draft.get('price')} грн · 📸 {len(photos)} фото\n"
                f"🔗 {res.get('url','')}\n"
                f"🆔 ad_id: {res.get('ad_id','')}")
            # удаляем черновик только если с with_inventory уже создан
            if with_inventory:
                _inventory_drafts.pop(draft_id, None)
                _pending_add_photo.pop(chat_id, None)
            else:
                # оставляем черновик для склада, но можно показать кнопки снова
                api.send_message(chat_id,
                    f"Хочешь также добавить на склад? Нажми ✅ Подтвердить",
                    reply_markup={
                        "inline_keyboard": [[
                            {"text": f"✅ На склад {draft.get('price')} грн", "callback_data": f"inv_confirm_{draft_id}"},
                            {"text": "❌ Отмена", "callback_data": f"inv_cancel_{draft_id}"}
                        ]]
                    })
        elif res.get("status") == "draft_created":
            api.send_message(chat_id,
                f"📝 <b>Черновик OLX создан (требует подтверждения телефона)</b>\n"
                f"📦 { _esc_tg(name) }\n"
                f"💰 {draft.get('price')} грн\n"
                f"Заверши публикацию через VNC :1 (Chrome профиль)")
        else:
            # need_confirm или ok (сгенерировано, но не опубликовано)
            title = res.get("title") or name
            desc = res.get("description") or ""
            price = res.get("price") or draft.get("price")
            kb = {
                "inline_keyboard": [[
                    {"text": "📢 Опубликовать на OLX", "callback_data": f"inv_olx_confirm_{draft_id}"},
                    {"text": "❌ Отмена", "callback_data": f"inv_cancel_{draft_id}"}
                ]]
            }
            api.send_message(chat_id,
                f"📝 <b>Объявление сгенерировано:</b>\n"
                f"Заголовок: <b>{_esc_tg(title[:80])}</b>\n"
                f"Цена: {price} грн\n"
                f"Описание: {_esc_tg(desc[:400])}\n\n"
                f"Публиковать?",
                reply_markup=kb)
    else:
        api.send_message(chat_id, f"❌ Не удалось создать OLX: {_esc_tg(res.get('error','?')[:400])}")
    return True


def _inv_do_confirm_and_olx(api, chat_id, cb_id, draft_id, msg_id=0):
    return _inv_do_create_olx(api, chat_id, cb_id, draft_id, with_inventory=True)



def _handle_button(api: TelegramAPI, chat_id: int, data: str) -> None:
    """Handle a callback, requiring an explicit second click for dangerous actions."""
    if data in DANGEROUS_CALLBACKS:
        _pending_confirmations[chat_id] = data
        api.send_message(
            chat_id,
            "⚠️ <b>Подтвердите опасное действие</b>",
            reply_markup={"inline_keyboard": [[
                {"text": "✅ Подтвердить", "callback_data": "confirm_dangerous"},
                {"text": "✖️ Отмена", "callback_data": "cancel_dangerous"},
            ]]},
        )
        return
    if data == "cancel_dangerous":
        _pending_confirmations.pop(chat_id, None)
        api.send_message(chat_id, "Действие отменено.")
        return
    if data == "confirm_dangerous":
        data = _pending_confirmations.pop(chat_id, "")
        if not data:
            api.send_message(chat_id, "Нет ожидающего действия для подтверждения.")
            return
    try:
        _handle_button_inner(api, chat_id, data)
    except Exception as e:
        print(f"  [BTN CRASH] {data}: {e}")
        import traceback; traceback.print_exc()
        try:
            api.send_message(chat_id, "Error: " + str(e)[:200])
        except:
            pass


def _handle_button_inner(api: TelegramAPI, chat_id: int, data: str) -> None:
    reply = None
    keyboard = None

    if data == "system_health":
        reply = _m().cmd_system_health()
    elif data == "last_backup":
        reply = _m().cmd_last_backup()
    elif data == "alert_history":
        reply = _m().cmd_alert_history()
    elif data == "menu_back":
        reply = chr(127899) + " <b>AIOS Control Panel</b>" + chr(10) + chr(10) + chr(129504) + " Koder 24/7"
        keyboard = MAIN_MENU_KEYBOARD
    elif data == "menu_stats":
        reply = _m().cmd_stats()
    elif data == "menu_platforms":
        reply = _m().cmd_platforms()
    elif data == "menu_help":
        reply = _m().cmd_help()
    elif data == "menu_coder":
        reply = chr(129504) + " <b>Koder</b>" + chr(10) + chr(10) + "Vyberite deistvie:"
        keyboard = CODER_MENU_KEYBOARD
    elif data == "menu_olx":
        reply = chr(128722) + " <b>OLX</b>"
        keyboard = OLX_MENU_KEYBOARD
    elif data == "phone_center":
        _handle_phone_control_center_intent(api, chat_id, "центр телефона")
        return
    elif data == "phone_recovery":
        _handle_phone_recovery_intent(api, chat_id, "восстановление телефона")
        return
    elif data == "phone_leads":
        _handle_phone_lead_intent(api, chat_id, "лиды телефона")
        return
    elif data == "phone_crm_tasks":
        _handle_phone_lead_intent(api, chat_id, "CRM задачи телефона")
        return
    elif data == "phone_banks":
        _handle_phone_bank_monitor_intent(api, chat_id, "статус банков телефона")
        return
    elif data == "phone_trends":
        _handle_phone_metrics_intent(api, chat_id, "тренды телефона")
        return
    elif data == "phone_sync":
        _handle_phone_recovery_intent(api, chat_id, "статус синхронизации телефона")
        return
    elif data == "phone_audit":
        _handle_phone_audit_intent(api, chat_id, "журнал телефона")
        return
    elif data == "phone_calibrations":
        _handle_phone_metrics_intent(api, chat_id, "калибровки телефона")
        return
    elif data == "phone_routes":
        api.send_message(chat_id, "🚕 <b>Маршруты</b>\n«маршрут Uklon: откуда -> куда»\n«маршрут EasyWay: остановка или адрес»\n\nАдрес и заказ выбираются вручную.")
        return
    elif data == "phone_workflows":
        _handle_phone_workflow_readiness_intent(api, chat_id, "проверка сценариев телефона")
        return
    elif data == "phone_data_health":
        _handle_phone_recovery_intent(api, chat_id, "здоровье данных телефона")
        return
    elif data == "phone_inventory":
        _handle_phone_inventory_intent(api, chat_id, "инвентарь телефона")
        return
    elif data == "phone_metrics_export":
        _handle_phone_metrics_intent(api, chat_id, "экспорт метрик телефона")
        return
    elif data == "menu_accounts":
        reply = cmd_accounts()
        keyboard = ACCOUNTS_MENU_KEYBOARD
    elif data == "menu_phone":
        reply = ("📲 <b>Телефон AIOS</b>\n\n"
                 "Центр, лиды, CRM follow-up, банки, метрики, синхронизации и журнал доступны через кнопки ниже. "
                 "Маршруты и сообщения остаются подтверждаемыми действиями.")
        keyboard = PHONE_MENU_KEYBOARD
    elif data == "accounts_google":
        reply = "🌐 <b>Google аккаунт</b> (jo.talbot@gmail.com)\n\nВыберите действие — или просто напишите «проверь почту» / «покажи календарь»."
        keyboard = GOOGLE_MENU_KEYBOARD
    elif data == "accounts_instagram":
        reply = "📸 <b>Instagram</b> (@jo.talbot)\n\nВыберите действие — или просто напишите «мой инстаграм» / «мои посты»."
        keyboard = INSTAGRAM_MENU_KEYBOARD
    elif data == "accounts_back":
        reply = cmd_accounts()
        keyboard = ACCOUNTS_MENU_KEYBOARD
    elif data == "accounts_facebook":
        reply = None
        keyboard = None
        api.send_message(chat_id, "⏳ Facebook…")
        _run_acct_cmd(api, chat_id, ["facebook", "profile"], "facebook")
    elif data == "accounts_tiktok":
        reply = None
        keyboard = None
        api.send_message(chat_id, "⏳ TikTok…")
        _run_acct_cmd(api, chat_id, ["tiktok", "profile"], "tiktok")
    elif data == "accounts_olx":
        reply = None
        keyboard = None
        api.send_message(chat_id, "⏳ OLX…")
        _run_acct_cmd(api, chat_id, ["olx", "profile"], "olx")
    elif data == "google_whoami":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "whoami")
    elif data == "google_unread":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "unread")
    elif data == "google_list":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "list")
    elif data == "google_calendar":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "calendar")
    elif data == "google_drive":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "drive")
    elif data == "google_mailshot":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "mailshot")
    elif data == "google_events":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "events")
    elif data == "google_event_add":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "event_prompt")
    elif data == "google_search":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "search_prompt")
    elif data == "google_docs":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "docs_prompt")
    elif data == "google_send":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "send_prompt")
    elif data == "ig_profile":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "profile")
    elif data == "ig_stats":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "stats")
    elif data == "ig_posts":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "posts")
    elif data == "ig_screenshot":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "screenshot")
    elif data == "ig_like_prompt":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "like_prompt")
    elif data == "ig_follow_prompt":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "follow_prompt")
    elif data == "ig_dm_prompt":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "dm_prompt")
    elif data == "menu_bot":
        reply = chr(129302) + " <b>Bot</b>"
        keyboard = BOT_MENU_KEYBOARD
    elif data == "menu_server":
        import subprocess as _sp
        try:
            uptime = _sp.run(["uptime", "-p"], capture_output=True, text=True, timeout=5).stdout.strip()
            mem = _sp.run(["free", "-h"], capture_output=True, text=True, timeout=5).stdout
            lines = [chr(128421) + " <b>Server</b>", "", chr(9201) + " " + uptime, ""]
            for l in mem.strip().split(chr(10))[:2]:
                lines.append(chr(128190) + " " + l.strip())
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
    elif data == "menu_docker":
        import subprocess as _sp
        try:
            ps = _sp.run(["docker", "ps", "--format", "{{.Names}}: {{.Status}}"], capture_output=True, text=True, timeout=10)
            lines = [chr(128051) + " <b>Docker</b>", ""]
            for l in ps.stdout.strip().split(chr(10)):
                if l:
                    name, st = (l.split(": ", 1) if ": " in l else (l, ""))
                    em = chr(9989) if "Up" in st else chr(10060)
                    lines.append(em + " <b>" + name + "</b> " + st)
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
    elif data == "menu_keys":
        import importlib.util as _iu, sys as _sys, os as _os
        try:
            spec = _iu.spec_from_file_location("lb_k", str(PROJECT_ROOT / "aios_core" / "llm_balancer.py"))
            mod = _iu.module_from_spec(spec)
            _sys.modules["lb_k"] = mod
            spec.loader.exec_module(mod)
            b = mod.LLMBalancer()
            s = b.status()
            total_k = sum(p.get("keys_total", 0) for p in s.get("providers", {}).values())
            avail_k = sum(p.get("keys_available", 0) for p in s.get("providers", {}).values())
            lines = [chr(128273) + " <b>API Keys</b> (" + str(avail_k) + "/" + str(total_k) + ")", ""]
            for pn, pd in s.get("providers", {}).items():
                a = pd.get("keys_available", 0)
                t = pd.get("keys_total", 0)
                bar = chr(128994) * a + chr(128308) * (t - a)
                lines.append("<b>" + pn.upper() + "</b> " + bar + " " + str(a) + "/" + str(t))
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
    elif data == "menu_logs":
        import subprocess as _sp
        try:
            logs = _sp.run(["tail", "-15", "/root/AIOS/logs/coder_orchestrator.log"], capture_output=True, text=True, timeout=5)
            t = logs.stdout.strip() or "Empty"
            reply = chr(128203) + " <b>Logs</b>" + chr(10) + chr(10) + "<pre>" + t[:3000].replace("<", "&lt;") + "</pre>"
        except Exception as e:
            reply = chr(10060) + " " + str(e)
    elif data == "coder_status":
        reply = _m().cmd_coder_status()
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_backlog":
        import json as _j
        try:
            with open(PROJECT_ROOT / "data" / "coder_backlog.json") as f:
                bl = _j.load(f)
            lines = [chr(128230) + " <b>Backlog</b>", ""]
            lines.append("Cycles: " + str(bl.get("cycle_count", 0)))
            lines.append(chr(9989) + " Done: " + str(bl.get("completed", 0)))
            lines.append(chr(10060) + " Failed: " + str(bl.get("failed", 0)))
            tasks = bl.get("tasks", [])
            if tasks:
                lines.append("")
                lines.append("<b>Tasks:</b>")
                for i, t in enumerate(tasks[:5], 1):
                    lines.append("  " + str(i) + ". " + t.get("description", "?")[:60])
            hist = bl.get("history", [])
            if hist:
                lines.append("")
                lines.append("<b>History (last 5):</b>")
                for h in hist[-5:]:
                    em = chr(9989) if h.get("status") == "pushed" else chr(9208)
                    lines.append("  " + em + " " + h.get("description", "?")[:50])
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_balancer":
        import importlib.util as _iu, sys as _sys
        try:
            spec = _iu.spec_from_file_location("lb_b", str(PROJECT_ROOT / "aios_core" / "llm_balancer.py"))
            mod = _iu.module_from_spec(spec)
            _sys.modules["lb_b"] = mod
            spec.loader.exec_module(mod)
            b = mod.LLMBalancer()
            s = b.status()
            lines = [chr(9878) + " <b>Balancer</b>", ""]
            lines.append("Requests: " + str(s.get("total_requests", 0)))
            lines.append("Errors: " + str(s.get("total_errors", 0)))
            lines.append("")
            for pn, pd in s.get("providers", {}).items():
                a = pd.get("keys_available", 0)
                t = pd.get("keys_total", 0)
                em = chr(9989) if a > 0 else chr(10060)
                lines.append(em + " <b>" + pn.upper() + "</b>: " + str(a) + "/" + str(t))
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_git_status":
        try:
            mod = _m()._get_coder_module()
            coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
            gs = coder.git.status()
            reply = chr(128220) + " <b>Git</b>" + chr(10) + chr(10) + (gs or chr(9989) + " Clean")
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_git_push":
        try:
            mod = _m()._get_coder_module()
            coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
            ok, out = coder.git.push()
            reply = chr(128640) + " " + ("Pushed" if ok else out[:200])
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_review_bot":
        reply = _m().cmd_code_review("run_telegram_bot.py")
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_review_self":
        reply = _m().cmd_code_review("aios_core/meta_cognitive_self_coder.py")
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_gen_prompt":
        _pending_actions[chat_id] = "gen_code"
        reply = chr(9997) + " <b>Send description of what to generate</b>"
    elif data == "coder_fix_prompt":
        _pending_actions[chat_id] = "fix_bug"
        reply = chr(128295) + " <b>Send: filename bug_description</b>"
    elif data == "coder_restart":
        import subprocess as _sp
        try:
            _sp.run(["systemctl", "restart", "aios-auto-coder"], timeout=10)
            reply = chr(128260) + " <b>Orchestrator restarted!</b>"
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "olx_stats":
        reply = _m().cmd_olx("")
        keyboard = OLX_MENU_KEYBOARD
    elif data == "olx_list":
        reply = _m().cmd_olx_list(chat_id)
        keyboard = OLX_MENU_KEYBOARD
    elif data == "olx_latest":
        reply = _m().cmd_olx_latest("", chat_id)
        keyboard = OLX_MENU_KEYBOARD
    elif data == "olx_analytics":
        reply = "Use: <code>/olx_analytics query</code>"
        keyboard = OLX_MENU_KEYBOARD
    elif data == "bot_start":
        import subprocess as _sp
        try:
            _sp.run(["docker", "compose", "-f", "/root/AIOS/docker-compose.prod.yml", "start", "aios-telegram-bot"], timeout=15)
            reply = chr(9654) + " <b>Bot started!</b>"
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = BOT_MENU_KEYBOARD
    elif data == "bot_pause":
        _m()._paused = not getattr(_m(), "_paused", False)
        if _m()._paused:
            reply = chr(9208) + " <b>Bot paused</b>" + chr(10) + "Messages skipped. Press again to resume."
        else:
            reply = chr(9654) + " <b>Bot resumed!</b>"
        keyboard = BOT_MENU_KEYBOARD
    elif data == "bot_restart":
        import subprocess as _sp
        try:
            _sp.run(["docker", "compose", "-f", "/root/AIOS/docker-compose.prod.yml", "restart", "aios-telegram-bot"], timeout=30)
            reply = chr(9989) + " <b>Bot restarted!</b>"
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = BOT_MENU_KEYBOARD
    elif data == "bot_stop":
        import subprocess as _sp
        try:
            api.send_message(chat_id, chr(9209) + " <b>Bot stopping...</b>")
            _sp.run(["docker", "compose", "-f", "/root/AIOS/docker-compose.prod.yml", "stop", "aios-telegram-bot"], timeout=30)
        except:
            pass
        return
    elif data == "bot_status":
        import subprocess as _sp
        try:
            ps = _sp.run(["docker", "ps", "-a", "--filter", "name=aios-telegram-bot", "--format", "{{.Status}}"], capture_output=True, text=True, timeout=5)
            reply = chr(128202) + " <b>Bot Status</b>" + chr(10) + chr(10) + (ps.stdout.strip() or "Not found")
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = BOT_MENU_KEYBOARD
    elif data == "bot_llm_gemini":
        try:
            from aios_core.llm_gemini_web import gemini_web_status, set_llm_mode
            st = gemini_web_status()
            set_llm_mode(chat_id, "gemini")
            if not st.get("chrome"):
                reply = "❌ <b>Gemini Web недоступен:</b> Chrome (CDP :9222) не найден.\nПроверьте: systemctl status aios-chrome-vnc"
            elif not st.get("logged_in"):
                reply = "⚠️ <b>Режим переключён на Gemini Web</b>, но Google-сессия не активна.\nВойдите в аккаунт в профиле chrome_twin (VNC :1) и повторите."
            else:
                reply = "🌐 <b>Режим LLM: Gemini Web</b>\n\nОтветы в этом чате идут через gemini.google.com (ваш профиль, временный чат)."
            keyboard = BOT_MENU_KEYBOARD
        except Exception as e:
            reply = "❌ " + str(e)[:200]
    elif data == "bot_llm_auto":
        try:
            from aios_core.llm_gemini_web import set_llm_mode
            set_llm_mode(chat_id, "auto")
            reply = "🔄 <b>Режим LLM: балансер</b>\n\nОбычный мульти-провайдерный LLM (groq/mistral/zai/... + Ollama)."
            keyboard = BOT_MENU_KEYBOARD
        except Exception as e:
            reply = "❌ " + str(e)[:200]

    if reply:
        try:
            if keyboard:
                api.send_message(chat_id, reply, reply_markup=keyboard)
            else:
                api.send_message(chat_id, reply)
        except Exception as e:
            print(f"  [BTN SEND ERR] {data}: {e}")
            try:
                api.send_message(chat_id, str(reply)[:3900], parse_mode="")
            except Exception as e2:
                print(f"  [BTN SEND ERR2] {e2}")
    else:
        print(f"  [BTN] no reply generated for: {data}")


def _handle_inbox_callback(api: TelegramAPI, chat_id: int, msg_id: int, data: str) -> None:
    """Обработка кнопок инбокса: прочитать пункт / всё прочитано / сводка."""
    items = _last_inbox.get(chat_id, [])
    if data == "inbox_refresh":
        _m()._send_unified_inbox(api, chat_id, filters=_last_inbox_filters.get(chat_id, {}),
                            refresh=True)
        return
    if data == "inbox_readall":
        _inbox_mark_read(api, chat_id)
        return
    if data == "inbox_summary":
        if not items:
            api.send_message(chat_id, "📭 Нет данных инбокса (соберите «инбокс» заново).")
            return
        api.send_message(chat_id, "🧠 Составляю умное резюме…")
        api.send_message(chat_id, _inbox_summarize(items)[:3900])
        return
    if data.startswith("inbox_read_"):
        try:
            idx = int(data.split("_")[-1])
            it = items[idx - 1]
        except Exception:
            api.send_message(chat_id, "❌ Не удалось открыть пункт.")
            return
        if it.get("channel") == "viber":
            api.send_message(chat_id, "⏳ Читаю выбранный Viber-чат…")
            data_vb = _run_account_control(["viber", "read", str(it.get("ref") or ""), "--limit", "12"])
            if data_vb.get("status") != "ok":
                api.send_message(chat_id, f"❌ Viber: {_esc_tg(data_vb.get('error', '?'))}")
                return
            messages = data_vb.get("messages") or []
            if not messages:
                api.send_message(chat_id, "💜 В выбранном Viber-чате нет распознанных сообщений.")
                return
            lines_vb = [f"💜 <b>{_esc_tg(it['title'])[:80]}</b> [Viber]"]
            for message in messages[-12:]:
                prefix = "↗️" if message.get("mine") else "•"
                lines_vb.append(f"{prefix} {_esc_tg(str(message.get('text') or '')[:220])}")
            lines_vb.append(f"\nОтветить: «ответь на {idx}: текст»")
            api.send_message(chat_id, "\n".join(lines_vb)[:3900])
            return
        if it.get("channel") == "signal":
            api.send_message(chat_id, "⏳ Читаю выбранный Signal-чат…")
            data_sig = _run_account_control(["signal", "read", str(it.get("ref") or ""), "--limit", "12"])
            if data_sig.get("status") != "ok":
                api.send_message(chat_id, f"❌ Signal: {_esc_tg(data_sig.get('error', '?'))}")
                return
            messages = data_sig.get("messages") or []
            if not messages:
                api.send_message(chat_id, "🔒 В выбранном Signal-чате нет распознанных сообщений.")
                return
            lines_sig = [f"🔒 <b>{_esc_tg(it['title'])[:80]}</b> [Signal]"]
            for message in messages[-12:]:
                prefix = "↗️" if message.get("mine") else "•"
                lines_sig.append(f"{prefix} {_esc_tg(str(message.get('text') or '')[:220])}")
            lines_sig.append(f"\nОтветить: «ответь на {idx}: текст»")
            api.send_message(chat_id, "\n".join(lines_sig)[:3900])
            return
        em, ch = _CHANNELS.get(it["channel"], ("", it["channel"]))
        txt = (f"{em} <b>{_esc_tg(it['title'])[:80]}</b> [{ch}]\n"
               f"{_esc_tg(it.get('preview') or '')}\n"
               f"🕐 {it.get('date') or '—'}\n\n"
               f"Ответить: «ответь на {idx}: текст»")
        api.send_message(chat_id, txt)
        return


def _handle_olx_send_callback(api: TelegramAPI, chat_id: int, cb_id: str, data: str) -> None:
    """Кнопка «Отправить ответ» — отправляет сгенерированный ответ в OLX-чат.

    Формат data: olx_send_<contact>|<text>. Контакт и текст URL-безопасно кодируются.
    """
    try:
        rid = data[len("olx_send_"):]
        # получить неотправленный ответ из pending-файла
        import json as _json
        pending = PROJECT_ROOT / "data" / "olx_pending_replies.json"
        item = None
        try:
            if pending.exists():
                _d = _json.loads(pending.read_text(encoding="utf-8"))
                item = _d.pop(rid, None)
                pending.write_text(_json.dumps(_d, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        if not item or not item.get("contact") or not item.get("text"):
            api.answer_callback(cb_id, "❌ Ответ не найден (истёк)")
            return
        contact = item["contact"]
        text = item["text"]
        import subprocess as _sp_olx
        r = _sp_olx.run(
            ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24",
             "/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
             "olx", "chat", "reply", contact, text, "--confirm"],
            capture_output=True, text=True, timeout=200, cwd=str(PROJECT_ROOT))
        out = (r.stdout or "").strip()
        ok = '"status": "sent"' in out or '"status": "ok"' in out
        if ok:
            api.answer_callback(cb_id, "✅ Отправлено")
            api.send_message(chat_id, f"✅ Ответ отправлен <b>{contact}</b> в OLX.")
        else:
            api.answer_callback(cb_id, "⚠️ Не отправлено")
            api.send_message(chat_id, f"⚠️ Не удалось отправить <b>{contact}</b>: {out[-200:]}")
    except Exception as e:
        try:
            api.answer_callback(cb_id, "⚠️ Ошибка")
            api.send_message(chat_id, f"⚠️ Ошибка отправки: {e}")
        except Exception:
            pass


def _handle_autonomy_callback(api: TelegramAPI, chat_id: int, msg_id: int, cb_id: str, data: str) -> None:
    """Обработка кнопок подтверждения/отклонения автономии."""
    try:
        approve = data.startswith("aut_ap_")
        aid = data.split("_", 2)[2]
        from aios_core.autonomy import AutonomyCore as _AutoCore
        core = _AutoCore()
        res = core.confirm(aid, approve=approve)
        if res.get("ok"):
            if approve:
                r = res.get("result", {})
                api.answer_callback(cb_id, "✅ Выполнено")
                api.send_message(chat_id,
                                 f"✅ <b>Подтверждено и выполнено</b> ({aid})\n"
                                 f"{r.get('message') or r.get('status') or 'ok'}")
            else:
                api.answer_callback(cb_id, "❌ Отклонено")
                api.send_message(chat_id, f"❌ Отклонено ({aid})")
        else:
            api.answer_callback(cb_id, "⚠️ не найдено")
            api.send_message(chat_id, f"⚠️ Approval {aid} не найден или уже обработан.")
    except Exception as e:
        try:
            api.answer_callback(cb_id, "⚠️ ошибка")
            api.send_message(chat_id, f"⚠️ Ошибка обработки кнопки: {e}")
        except Exception:
            pass


def _handle_viber_draft_callback(api: TelegramAPI, chat_id: int, cb_id: str, data: str) -> None:
    """Подтвердить или отменить Viber-черновик из фонового обработчика."""
    try:
        from viber_drafts import ViberDraftStore
        send = data.startswith("viber_draft_send_")
        prefix = "viber_draft_send_" if send else "viber_draft_cancel_"
        draft_id = data[len(prefix):]
        store = ViberDraftStore(PROJECT_ROOT)
        if not draft_id:
            api.answer_callback(cb_id, "❌ Некорректный черновик")
            return
        if not send:
            draft = store.cancel(draft_id)
            if draft is None:
                api.answer_callback(cb_id, "ℹ️ Уже обработан")
                return
            api.answer_callback(cb_id, "❌ Черновик отклонён")
            api.send_message(chat_id, f"💜 Черновик для <b>{_esc_tg(draft.get('contact'))}</b> отклонён.")
            return
        draft = store.claim(draft_id)
        if draft is None:
            api.answer_callback(cb_id, "ℹ️ Уже обработан")
            return
        result = _run_account_control([
            "viber", "send", str(draft.get("contact") or ""),
            str(draft.get("text") or ""), "--confirm",
        ])
        if result.get("status") == "sent":
            store.finalize(draft_id, sent=True)
            api.answer_callback(cb_id, "✅ Отправлено")
            api.send_message(chat_id, f"✅ Черновик отправлен в Viber: <b>{_esc_tg(draft.get('contact'))}</b>.")
        else:
            error = str(result.get("error") or result.get("status") or "неизвестная ошибка")
            store.finalize(draft_id, sent=False, error=error)
            api.answer_callback(cb_id, "⚠️ Не отправлено")
            api.send_message(chat_id, f"⚠️ Viber не отправил черновик: {_esc_tg(error)[:220]}")
    except Exception as exc:
        try:
            api.answer_callback(cb_id, "⚠️ Ошибка")
            api.send_message(chat_id, f"⚠️ Ошибка Viber-черновика: {_esc_tg(str(exc))[:220]}")
        except Exception:
            pass


def _handle_signal_draft_callback(api: TelegramAPI, chat_id: int, cb_id: str, data: str) -> None:
    """Подтвердить или отменить Signal-черновик из фонового обработчика."""
    try:
        from signal_drafts import SignalDraftStore
        send = data.startswith("signal_draft_send_")
        prefix = "signal_draft_send_" if send else "signal_draft_cancel_"
        draft_id = data[len(prefix):]
        store = SignalDraftStore(PROJECT_ROOT)
        if not draft_id:
            api.answer_callback(cb_id, "❌ Некорректный черновик")
            return
        if not send:
            draft = store.cancel(draft_id)
            if draft is None:
                api.answer_callback(cb_id, "ℹ️ Уже обработан")
                return
            api.answer_callback(cb_id, "❌ Черновик отклонён")
            api.send_message(chat_id, f"🔒 Черновик для <b>{_esc_tg(draft.get('contact'))}</b> отклонён.")
            return
        draft = store.claim(draft_id)
        if draft is None:
            api.answer_callback(cb_id, "ℹ️ Уже обработан")
            return
        result = _run_account_control([
            "signal", "send", str(draft.get("contact") or ""),
            str(draft.get("text") or ""), "--confirm",
        ])
        if result.get("status") == "sent":
            store.finalize(draft_id, sent=True)
            api.answer_callback(cb_id, "✅ Отправлено")
            api.send_message(chat_id, f"✅ Черновик отправлен в Signal: <b>{_esc_tg(draft.get('contact'))}</b>.")
        else:
            error = str(result.get("error") or result.get("status") or "неизвестная ошибка")
            store.finalize(draft_id, sent=False, error=error)
            api.answer_callback(cb_id, "⚠️ Не отправлено")
            api.send_message(chat_id, f"⚠️ Signal не отправил черновик: {_esc_tg(error)[:220]}")
    except Exception as exc:
        try:
            api.answer_callback(cb_id, "⚠️ Ошибка")
            api.send_message(chat_id, f"⚠️ Ошибка Signal-черновика: {_esc_tg(str(exc))[:220]}")
        except Exception:
            pass


def _handle_callback(api: TelegramAPI, upd: dict) -> None:
    """Handle inline button callbacks (кнопки в сообщениях)."""
    cb = upd.get("callback_query", {})
    cb_id = cb.get("id", "")
    data = cb.get("data", "")
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")

    if not chat_id or not data:
        return

    # ---- Inventory draft (фича v22.1) — перехватываем до общего answer_callback, иначе лишний спам ----
    if data in ("noop",):
        api.answer_callback(cb_id, "…")
        return

    if data.startswith("nav_") or data.startswith("olx_") or data.startswith("cat_items_") or data.startswith("crypto_"):
        _handle_nav_callback(api, chat_id, cb_id, data)
        return

    if data.startswith("inv_"):
        # не шлём общий "Обрабатываю", т.к. _handle_inventory_callback сам ответит
        if _handle_inventory_callback(api, chat_id, cb_id, data, msg_id):
            return

    # ---- Каталог/навигация (v22.7): inline-кнопки сводки и склада ----
    if data in ("cat_warehouse", "cat_competitors", "cat_design", "cat_freelance"):
        api.answer_callback(cb_id, "Открываю…")
        try:
            from tg_bot.catalog import _handle_catalog_intent, _handle_catalog_design_intent, _handle_competitors_intent
            if data == "cat_warehouse":
                _handle_catalog_intent(api, chat_id, "склад")
            elif data == "cat_competitors":
                _handle_competitors_intent(api, chat_id, "конкуренты")
            elif data == "cat_design":
                _handle_catalog_design_intent(api, chat_id, "дизайн каталога")
            elif data == "cat_freelance":
                from tg_bot.dashboard import _handle_dashboard_intent
                _handle_dashboard_intent(api, chat_id, "сводка фриланс")
        except Exception as _e:
            api.send_message(chat_id, f"⚠️ Ошибка навигации: {_e}")
        return

    api.answer_callback(cb_id, "⏳ Обрабатываю...")

    # ---- Signal: черновик из фонового безопасного обработчика ----
    if data.startswith("signal_draft_send_") or data.startswith("signal_draft_cancel_"):
        _handle_signal_draft_callback(api, chat_id, cb_id, data)
        return

    # ---- Viber: черновик из фонового безопасного обработчика ----
    if data.startswith("viber_draft_send_") or data.startswith("viber_draft_cancel_"):
        _handle_viber_draft_callback(api, chat_id, cb_id, data)
        return

    # ---- OLX: отправить сгенерированный ответ вручную (кнопка) ----
    if data.startswith("olx_send_"):
        _handle_olx_send_callback(api, chat_id, cb_id, data)
        return

    # ---- Автономия: кнопки подтверждения/отклонения ----
    if data.startswith("aut_ap_") or data.startswith("aut_rm_"):
        _handle_autonomy_callback(api, chat_id, msg_id, cb_id, data)
        return

    # ---- Инбокс: inline-действия ----
    if data.startswith("inbox_"):
        _handle_inbox_callback(api, chat_id, msg_id, data)
        return

    # ---- Инбокс: inline-действия ----
    if data.startswith("inbox_"):
        _handle_inbox_callback(api, chat_id, msg_id, data)
        return

    # ---- Остальные кнопки меню (опасные — с подтверждением) ----
    _handle_button(api, chat_id, data)


def _handle_nav_callback(api, chat_id: int, cb_id: str, data: str) -> None:
    """Навигация по inline-меню (v22.8): nav_*, olx_*, cat_items_*."""
    api.answer_callback(cb_id, "⏳ Открываю…")
    try:
        import run_telegram_bot as _bot
        if data == "nav_dashboard":
            from tg_bot.dashboard import _handle_dashboard_intent
            _handle_dashboard_intent(api, chat_id, "сводка")
        elif data == "nav_catalog":
            from tg_bot.catalog import _handle_catalog_intent
            _handle_catalog_intent(api, chat_id, "склад")
        elif data == "nav_competitors":
            from tg_bot.catalog import _handle_competitors_intent
            _handle_competitors_intent(api, chat_id, "конкуренты")
        elif data == "nav_olx":
            from tg_bot.keyboards import OLX_ACTIONS_INLINE
            api.send_message(chat_id, "🛒 <b>OLX</b> — выберите действие:", reply_markup=OLX_ACTIONS_INLINE)
        elif data == "nav_freelance":
            from tg_bot.dashboard import _handle_freelance_summary_intent
            _handle_freelance_summary_intent(api, chat_id, "фриланс")
        elif data == "nav_treasury":
            from tg_bot.treasury import _handle_treasury_intent as _hti
            _hti(api, chat_id, "казначейство и резервы")
        elif data in ("nav_trading", "crypto_refresh"):
            from tg_bot.treasury import _handle_treasury_intent as _hti
            _hti(api, chat_id, "крипто заработок")
        elif data == "crypto_chart":
            from tg_bot.treasury import _handle_treasury_intent as _hti
            _hti(api, chat_id, "крипто график")
        elif data == "crypto_positions":
            from tg_bot.treasury import _handle_treasury_intent as _hti
            _hti(api, chat_id, "крипто позиции")
        elif data in ("crypto_arb", "nav_arb"):
            from tg_bot.treasury import _handle_treasury_intent as _hti
            _hti(api, chat_id, "арбитраж")
        elif data == "nav_np":
            from tg_bot.treasury import _handle_treasury_intent as _hti
            _hti(api, chat_id, "логистика новая почта")
        elif data == "nav_phone":
            from tg_bot.phone import _handle_phone_control_center_intent as _hpc
            _hpc(api, chat_id, "центр телефона")
        elif data == "nav_sre":
            try:
                api.send_message(chat_id, _bot.cmd_system_health())
            except Exception as _e_sre:
                api.send_message(chat_id, f"🛡 SRE: временно недоступно ({_e_sre})")
        elif data == "nav_help":
            api.send_message(chat_id, _bot.cmd_help())
        elif data == "olx_stats":
            api.send_message(chat_id, _bot.cmd_olx(""))
        elif data == "olx_latest":
            api.send_message(chat_id, _bot.cmd_olx_latest("запчасти ваз б/у", chat_id))
        elif data == "olx_analytics":
            try:
                api.send_message(chat_id, _bot.cmd_olx_analytics("запчасти ваз"))
            except Exception as _e_olx:
                api.send_message(chat_id, f"⚠️ Аналитика OLX: {_e_olx}")
        elif data == "olx_subs":
            api.send_message(chat_id, _bot.cmd_olx_list(chat_id))
        elif data.startswith("cat_items_"):
            try:
                offset = int(data.split("_")[-1])
            except Exception:
                offset = 0
            from tg_bot.catalog import _send_items_page
            _send_items_page(api, chat_id, offset)
        else:
            api.answer_callback(cb_id, "Неизвестное действие")
    except Exception as e:
        try:
            api.send_message(chat_id, f"⚠️ Ошибка навигации: {e}")
        except Exception:
            pass
