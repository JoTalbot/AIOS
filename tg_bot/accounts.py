"""Аккаунты: Gmail/Instagram/календарь + центральный диспетчер интентов
(выделено из run_telegram_bot.py; взаимные вызовы монолита — через _m())."""
from __future__ import annotations

import base64
import contextlib
import imaplib
import json
import os
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from tg_bot.common import PROJECT_ROOT, _esc_tg, _run_account_control, _smart_model
from tg_bot.inbox import (
    _collect_inbox, _format_inbox, _inbox_keyboard, _inbox_mark_read, _inbox_reply,
    _inbox_schedule_cmd, _inbox_search, _inbox_summarize, _inbox_voice,
    _llm_chat_direct, _parse_inbox_filters,
)
from tg_bot.state import (
    _pending_confirm, _last_inbox, _last_photo, _photo_pending,
    _last_gen_ad, _last_video, _last_gmail_ids,
)
from tg_bot.voice import _set_voice_enabled, _send_voice_reply, _voice_enabled

def _m():
    """Lazy-доступ к монолиту run_telegram_bot (strangler: диспетчерские вызовы)."""
    import run_telegram_bot
    return run_telegram_bot



def _fmt_gmail_list(data: dict, unread_only: bool = False) -> str:
    emails = data.get("emails", [])
    if not emails:
        return "📭 Писем не найдено."
    head = f"📥 <b>{'Непрочитанные' if unread_only else 'Последние'} письма</b>\n"
    head += f"Всего: {data.get('total', '?')} · 🔴 непрочитанных: {data.get('unread_total', '?')}\n\n"
    lines = [head]
    for i, e in enumerate(emails, 1):
        if "error" in e:
            lines.append(f"{i}. ❌ {e['error']}")
            continue
        mark = "🔴 " if e.get("unread") else ""
        subj = e.get("subject", "(без темы)")
        frm = e.get("from", "?")
        date = (e.get("date") or "")[:22]
        snip = (e.get("snippet") or "")[:180]
        lines.append(f"{i}. {mark}<b>{subj}</b>\n   ✉️ {frm}\n   🕐 {date}\n   {snip}")
    return "\n\n".join(lines)


def _acct_send_result(api, chat_id: int, data: dict, intro: str) -> None:
    if data.get("status") == "error":
        api.send_message(chat_id, f"❌ {data.get('error', 'неизвестная ошибка')}")
        return
    api.send_message(chat_id, intro + (data.get("text", "")), parse_mode="HTML")
    shot = data.get("screenshot")
    if shot and os.path.exists(shot):
        try:
            api.send_photo(chat_id, shot, caption=data.get("caption", ""))
        except Exception as e:
            print(f"  [ACCT] send_photo failed: {e}")


def _run_acct_cmd(api, chat_id: int, args: list, kind: str) -> None:
    """Универсальный запуск команд аккаунтов (facebook/tiktok/olx)."""
    data = _run_account_control(args)
    if data.get("status") != "ok":
        api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
        return
    if kind == "facebook":
        f = data.get("facebook", {})
        txt = (f"📘 <b>Facebook</b>\n👤 Имя: {_esc_tg(f.get('name'))}\n"
               f"👥 Друзья: {f.get('friends') or '?'}\n"
               f"📍 {_esc_tg(f.get('city') or '—')}\n"
               f"ℹ️ {_esc_tg(f.get('bio') or 'без описания')}\n"
               f"🔗 {f.get('profile_url')}\n🔔 Уведомлений: {f.get('notifications') or 0}")
    elif kind == "tiktok":
        p = data.get("tiktok", {})
        txt = (f"🎵 <b>TikTok</b>\n👤 Имя: {_esc_tg(p.get('name') or p.get('username'))}\n"
               f"👥 Подписчики: {p.get('followers') or 0} · 🔄 Подписки: {p.get('following') or 0}\n"
               f"❤️ Лайки: {p.get('likes') or 0}\nℹ️ {_esc_tg(p.get('bio') or '—')}\n"
               f"🔗 {p.get('profile_url')}")
    elif kind == "olx":
        o = data.get("olx", {})
        txt = (f"🛒 <b>OLX</b>\n👤 Имя: {_esc_tg(o.get('name') or '?')}\n"
               f"📄 Объявлений: {o.get('ads_count') or 0}\n"
               f"💰 Баланс: {o.get('balance') or 0} грн\n🔑 Логин: {o.get('login')}")
    else:
        txt = str(data)[:300]
    _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                     "screenshot": data.get("screenshot") or
                                     (data.get("facebook") or data.get("tiktok") or data.get("olx") or {}).get("screenshot"),
                                     "caption": {"facebook": "📘 Facebook", "tiktok": "🎵 TikTok",
                                                 "olx": "🛒 OLX"}.get(kind, "")}, "")


def _acct_google(api, chat_id: int, kind: str, extra: str = "") -> None:
    api.send_message(chat_id, "⏳ Секунду, работаю с Google…")
    if kind == "whoami":
        data = _run_account_control(["google", "whoami"])
        if data.get("status") == "ok":
            email = data.get("email") or "?"
            raw = (data.get("raw") or email).replace("\n", " ")
            api.send_message(chat_id,
                             f"👤 <b>Google аккаунт в Chrome:</b>\n{raw}\n\n"
                             f"Почта (IMAP): <code>{email}</code>")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
    elif kind == "unread":
        data = _run_account_control(["google", "gmail_list", "5", "--unread"])
        if data.get("status") == "ok":
            _last_gmail_ids[chat_id] = [e.get("id", "") for e in data.get("emails", [])]
        _acct_send_result(api, chat_id, {"status": data.get("status"),
                                         "error": data.get("error"),
                                         "text": _fmt_gmail_list(data, unread_only=True)}, "")
    elif kind == "list":
        data = _run_account_control(["google", "gmail_list", "5"])
        if data.get("status") == "ok":
            _last_gmail_ids[chat_id] = [e.get("id", "") for e in data.get("emails", [])]
        _acct_send_result(api, chat_id, {"status": data.get("status"),
                                         "error": data.get("error"),
                                         "text": _fmt_gmail_list(data)}, "")
    elif kind == "calendar":
        data = _run_account_control(["google", "screenshot", "calendar"])
        _acct_send_result(api, chat_id,
                          {"status": data.get("status"), "error": data.get("error"),
                           "text": f"📅 <b>Google Календарь</b>\n{data.get('title', '')}\n{data.get('url', '')}",
                           "screenshot": data.get("screenshot"),
                           "caption": "📅 Календарь (скриншот)"}, "")
    elif kind == "drive":
        data = _run_account_control(["google", "screenshot", "drive"])
        _acct_send_result(api, chat_id,
                          {"status": data.get("status"), "error": data.get("error"),
                           "text": f"🗂 <b>Google Диск</b>\n{data.get('title', '')}\n{data.get('url', '')}",
                           "screenshot": data.get("screenshot"),
                           "caption": "🗂 Диск (скриншот)"}, "")
    elif kind == "mailshot":
        data = _run_account_control(["google", "screenshot", "gmail"])
        _acct_send_result(api, chat_id,
                          {"status": data.get("status"), "error": data.get("error"),
                           "text": f"📧 <b>Почта Gmail</b>\n{data.get('title', '')}\n{data.get('url', '')}",
                           "screenshot": data.get("screenshot"),
                           "caption": "📧 Gmail (скриншот)"}, "")
    elif kind == "events":
        data = _run_account_control(["google", "calendar_events"])
        if data.get("status") == "ok":
            evs = data.get("events") or []
            if evs:
                text = "📅 <b>События на сегодня:</b>\n" + "\n".join(f"• {e}" for e in evs)
            else:
                text = "📅 Событий на сегодня нет."
            _acct_send_result(api, chat_id, {"status": "ok", "text": text,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "📅 Календарь (сегодня)"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
    elif kind == "send_prompt":
        api.send_message(chat_id,
                         "📧 <b>Отправка письма</b>\n\n"
                         "Напишите одним сообщением: <i>кому, тема, текст</i>.\n"
                         "Например: «отправь письмо ivan@gmail.com, тема Встреча, "
                         "текст: привет, созвонимся завтра в 15:00»")
    elif kind == "event_prompt":
        api.send_message(chat_id,
                         "📅 <b>Создание события</b>\n\n"
                         "Напишите, например: «событие Встреча с Мишей завтра в 14:00»,\n"
                         "или «добавь событие Отчёт 05.08 в 10:30»")
    elif kind == "search_prompt":
        api.send_message(chat_id,
                         "🔍 <b>Поиск в почте</b>\n\n"
                         "Напишите «найди письмо &lt;запрос&gt;», например «найди письмо от github»")
    elif kind == "docs_prompt":
        api.send_message(chat_id,
                         "📄 <b>Создание документа</b>\n\n"
                         "Напишите «создай документ, тема <название>, текст: <содержимое>»")
    else:
        api.send_message(chat_id, "❌ Неизвестная команда Google.")


def _acct_instagram(api, chat_id: int, kind: str, extra: str = "") -> None:
    api.send_message(chat_id, "⏳ Секунду, захожу в Instagram…")
    if kind in ("profile", "stats"):
        data = _run_account_control(["instagram", "profile"])
        if data.get("status") == "ok":
            p = data.get("profile", {})
            text = (f"📸 <b>Instagram: @{p.get('username', '?')}</b>\n"
                    f"👤 Имя: {p.get('full_name') or '—'}\n"
                    f"👥 Подписчики: {p.get('followers') or 0}\n"
                    f"🔄 Подписки: {p.get('following') or 0}\n"
                    f"📄 Постов: {p.get('posts_count') or 0}\n"
                    f"ℹ️ {p.get('bio') or 'без описания'}\n"
                    f"🔗 {p.get('profile_url') or ''}")
            _acct_send_result(api, chat_id,
                              {"status": "ok", "text": text,
                               "screenshot": data.get("screenshot"),
                               "caption": f"📸 @{p.get('username')}"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
    elif kind == "posts":
        data = _run_account_control(["instagram", "posts", "5"])
        if data.get("status") == "ok":
            posts = data.get("posts") or []
            if not posts:
                api.send_message(chat_id,
                                 f"🖼 <b>@{(data.get('username') or '?')}</b>: постов пока нет.")
                return
            lines = [f"🖼 <b>Последние посты @{data.get('username')}</b>:"]
            for i, p in enumerate(posts, 1):
                alt = (p.get("alt") or "")[:80]
                lines.append(f"{i}. <a href=\"{p.get('url')}\">/p/{p.get('code')}</a>  {alt}")
            api.send_message(chat_id, "\n".join(lines))
        else:
            api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
    elif kind == "screenshot":
        data = _run_account_control(["instagram", "screenshot"])
        _acct_send_result(api, chat_id,
                          {"status": data.get("status"), "error": data.get("error"),
                           "text": f"📸 <b>Instagram</b>: @{data.get('username', '?')}",
                           "screenshot": data.get("screenshot"),
                           "caption": "📸 Профиль Instagram"}, "")
    elif kind == "like_prompt":
        api.send_message(chat_id,
                         "❤️ <b>Лайк</b>: пришлите ссылку на пост, например:\n"
                         "«лайкни https://www.instagram.com/p/CODE/»")
    elif kind == "follow_prompt":
        api.send_message(chat_id,
                         "👤 <b>Подписка</b>: напишите\n"
                         "«подпишись на @username» или «отпишись от @username»")
    elif kind == "dm_prompt":
        api.send_message(chat_id,
                         "💬 <b>Директ Instagram</b>\n\n"
                         "• «директ» — список чатов\n"
                         "• «покажи чат Серега» — последние сообщения\n"
                         "• «напиши в директ Серега: привет» — отправить (с подтверждением)\n"
                         "• «напиши в директ @username: текст» — новый чат")
    else:
        api.send_message(chat_id, "❌ Неизвестная команда Instagram.")


def _llm_extract_json(prompt: str) -> dict:
    """Универсальный LLM-вызов: вернуть JSON из промпта."""
    import urllib.request as _urllib
    _b = None
    try:
        from aios_core.llm_balancer import LLMBalancer as _LB
        _b = _LB()
    except Exception:
        _b = None
    response = None
    if _b is not None:
        try:
            response = _b.chat([{"role": "user", "content": prompt}],
                               model=_smart_model(),
                               system="You extract JSON only.", max_tokens=400, temperature=0.0,
                               task_type="chat")
        except Exception:
            response = None
    if not response:
        try:
            key = os.environ.get("OPENROUTER_API_KEY", "")
            if key:
                payload = json.dumps({
                    "model": "mistralai/mistral-small-3.2-24b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400, "temperature": 0.0,
                }).encode()
                req = _urllib.Request("https://openrouter.ai/api/v1/chat/completions",
                                      data=payload, headers={
                                          "Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
                with _urllib.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read())
                response = data["choices"][0]["message"]["content"]
        except Exception:
            pass
    if not response:
        return {}
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except Exception:
        pass
    return {}


def _llm_extract_gmail(text: str) -> dict:
    """LLM: извлечь {to, subject, body} из запроса на отправку письма."""
    prompt = (
        "Ты — парсер. Извлеки из сообщения данные для письма. "
        "Верни ТОЛЬКО JSON без пояснений: {\"to\": \"email\", \"subject\": \"тема\", \"body\": \"текст\"}. "
        "Если адреса нет — to=''. Если темы нет — subject=''. "
        f"Сообщение: {text}"
    )
    return _llm_extract_json(prompt)


def _llm_extract_calendar(text: str) -> dict:
    """LLM: извлечь {title, date, time, desc} из запроса на создание события."""
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    prompt = (
        "Ты — парсер событий календаря. Извлеки из сообщения данные события. "
        "Верни ТОЛЬКО JSON без пояснений: "
        "{\"title\": \"название\", \"date\": \"YYYY-MM-DD\", \"time\": \"HH:MM\", \"desc\": \"описание\"}. "
        f"Сегодня = {today}, завтра = {tomorrow}. Если дата не указана — date='' (значит сегодня). "
        "Если время не указано — time='' (значит 12:00). Если описания нет — desc=''. "
        f"Сообщение: {text}"
    )
    return _llm_extract_json(prompt)


def _handle_account_intent(api, chat_id: int, text: str) -> bool:
    """Обработать «человеческое» сообщение про Google/Instagram. True = обработано."""
    t = text.lower()

    # 1) подтверждение/отмена ожидающего действия
    if chat_id in _pending_confirm:
        yes = any(w in t for w in ("да", "отправь", "отправляй", "подтверж", "yes", "ага", "го", "ок", "давай"))
        no = any(w in t for w in ("нет", "отмена", "не надо", "no", "cancel", "стоп", "не отправляй", "не хочу"))
        if yes or no:
            pend = _pending_confirm.pop(chat_id)
            kind = pend.get("kind", "")
            if no:
                if _m()._cancel_phone_pending(api, chat_id, kind, pend.get("data") or {}):
                    return True
                api.send_message(chat_id, "🚫 Действие отменено.")
                return True
            if _m()._confirm_phone_pending(api, chat_id, kind, pend.get("data") or {}):
                return True
            if kind == "gmail":
                d = pend["data"]
                data = _run_account_control(["google", "gmail_send", "--to", d["to"],
                                             "--subject", d["subject"], "--body", d["body"],
                                             "--confirm"])
                if data.get("status") == "sent":
                    api.send_message(chat_id,
                                     f"✅ Письмо отправлено:\n📧 <b>{d['subject']}</b> → {d['to']}")
                else:
                    api.send_message(chat_id, f"❌ Ошибка отправки: {data.get('error', '?')}")
                return True
            if kind == "calendar_add":
                d = pend["data"]
                data = _run_account_control(["google", "calendar_add",
                                             "--title", d["title"], "--date", d.get("date", ""),
                                             "--time", d.get("time", ""), "--desc", d.get("desc", ""),
                                             "--confirm"])
                if data.get("status") == "ok":
                    api.send_message(chat_id,
                                     f"✅ Событие создано:\n📅 <b>{d['title']}</b>\n"
                                     f"🕐 {data.get('start', '')} → {data.get('end', '')}\n"
                                     f"🔗 {data.get('url', '')}")
                else:
                    api.send_message(chat_id, f"❌ Ошибка создания события: {data.get('error', '?')}")
                return True
            if kind == "ig_like":
                d = pend["data"]
                data = _run_account_control(["instagram", "like", d["url"], "--confirm"])
                st = data.get("status")
                if st == "liked":
                    api.send_message(chat_id, f"❤️ Лайк поставлен: {d['url']}")
                elif st == "already_liked":
                    api.send_message(chat_id, f"👍 Пост уже лайкнут: {d['url']}")
                else:
                    api.send_message(chat_id, f"❌ Ошибка: {data.get('error', st)}")
                return True
            if kind == "ig_unlike":
                d = pend["data"]
                data = _run_account_control(["instagram", "unlike", d["url"], "--confirm"])
                st = data.get("status")
                if st == "unliked":
                    api.send_message(chat_id, f"💔 Лайк убран: {d['url']}")
                else:
                    api.send_message(chat_id, f"ℹ️ {data.get('error', st)}")
                return True
            if kind == "olx_create":
                d = pend["data"]
                import subprocess as _sp
                _cmd_list = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"),
                             "create", d["part"], "--confirm"]
                _ph = _last_photo.get(chat_id, "")
                if _ph and os.path.exists(_ph):
                    _cmd_list += ["--photo", _ph]
                r = _sp.run(_cmd_list,
                            capture_output=True, text=True, timeout=240, cwd=str(PROJECT_ROOT))
                try:
                    data = json.loads((r.stdout or "").strip().split("\n")[-1])
                except Exception:
                    data = {"status": "error", "error": (r.stderr or r.stdout or "?")[-200:]}
                st = data.get("status")
                if st == "published":
                    txt = f"✅ <b>Объявление опубликовано на OLX!</b>\n{_esc_tg(data.get('title', ''))} — {data.get('price', '?')} грн\n{data.get('url', '')}"
                    _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                     "screenshot": data.get("screenshot"),
                                                     "caption": "✅ Опубликовано"}, "")
                elif st == "draft_created":
                    txt = f"📝 <b>Черновик создан</b>: {_esc_tg(data.get('title', ''))}\n"
                    if data.get("screenshot"):
                        _acct_send_result(api, chat_id, {"status": "ok",
                                                         "text": txt,
                                                         "screenshot": data.get("screenshot"),
                                                         "caption": "📝 OLX черновик"}, "")
                    else:
                        api.send_message(chat_id, txt)
                elif st == "phone_not_confirmed":
                    api.send_message(chat_id, f"📱 {data.get('error', 'Нужно подтвердить телефон')}\n"
                                              f"Напишите «подтверди телефон OLX».")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "ttn_create":
                d = pend["data"]
                import subprocess as _sp
                r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_ttn.py"),
                             "create", d["detail"], d["cost"], d["recipient"], d["phone"],
                             d["city"], d["warehouse"], "--confirm"],
                            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
                try:
                    data = json.loads((r.stdout or "").strip().split("\n")[-1])
                except Exception:
                    data = {"status": "error", "error": (r.stderr or "?")[-300:]}
                if data.get("status") == "ok":
                    lifecycle_line = ""
                    inventory = data.get("inventory") or {}
                    if data.get("task"):
                        lifecycle_line = (
                            f"\n\n📋 <b>Задача создана:</b> отправить товар по ТТН.\n"
                            f"После передачи в НП: «отправил {data.get('ttn')}»."
                        )
                    if inventory.get("status") == "error":
                        lifecycle_line += (f"\n⚠️ Резерв склада требует проверки: "
                                           f"{_esc_tg(inventory.get('error', '?'))}")
                    if data.get("sale_lifecycle_warning"):
                        lifecycle_line += (f"\n⚠️ Учёт продажи: "
                                           f"{_esc_tg(data.get('sale_lifecycle_warning'))}")
                    olx = data.get("olx") or {}
                    if olx.get("status") == "deactivated":
                        lifecycle_line += "\n🛒 Связанное объявление OLX снято с публикации."
                    elif olx.get("status") == "kept_active":
                        lifecycle_line += (f"\n🛒 Объявление OLX оставлено: в остатке ещё "
                                           f"{olx.get('available_qty')} шт.")
                    elif olx.get("status") in ("not_found", "ambiguous", "error"):
                        lifecycle_line += ("\n⚠️ Не удалось однозначно снять связанное объявление OLX: "
                                           "проверьте его вручную.")
                    api.send_message(chat_id,
                                     f"📦 <b>ТТН создана: {data.get('ttn')}</b>\n"
                                     f"Деталь: {_esc_tg(data.get('detail'))} · Стоимость: {data.get('cost')} грн\n"
                                     f"Получатель: {_esc_tg(data.get('recipient'))}\n"
                                     f"Отслеживание: «отследи {data.get('ttn')}»{lifecycle_line}")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', 'Ошибка')}")
                return True
            if kind == "olx_chat_reply":
                d = pend["data"]
                data = _run_account_control(["olx", "chat", "reply", d["to"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Ответ отправлен покупателю «{_esc_tg(d['to'])}».")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "olx_bulk":
                import subprocess as _sp
                api.send_message(chat_id, "⏳ Публикую объявления на OLX (по ~2-3 мин на каждое)…")
                r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"),
                             "export_sklad", "--confirm"],
                            capture_output=True, text=True, timeout=1500, cwd=str(PROJECT_ROOT))
                try:
                    data = json.loads((r.stdout or "").strip().split("\n")[-1])
                except Exception:
                    data = {"status": "error", "error": (r.stderr or r.stdout or "?")[-300:]}
                if data.get("status") == "ok":
                    lines = ["📦 <b>Выгрузка склада завершена</b>"]
                    for x in (data.get("results") or [])[:20]:
                        em = {"published": "✅", "draft": "📝", "error": "❌"}.get(x.get("status"), "❌")
                        lines.append(f"{em} {_esc_tg(x.get('name'))}: {x.get('status')} {x.get('error', '')[:60]}")
                    api.send_message(chat_id, "\n".join(lines)[:3900])
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', 'Ошибка выгрузки')}")
                return True
            if kind == "olx_delete":
                d = pend["data"]
                data = _run_account_control(["olx", "delete", d["ad_id"], "--confirm"])
                st = data.get("status")
                if st == "deleted":
                    api.send_message(chat_id, f"🗑 Объявление <b>{d['ad_id']}</b> удалено с OLX.")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "olx_edit":
                d = pend["data"]
                data = _run_account_control(["olx", "edit", d["ad_id"],
                                             "--title", d.get("title", ""),
                                             "--desc", d.get("description", ""),
                                             "--price", d.get("price", ""),
                                             "--confirm"])
                st = data.get("status")
                if st == "edited":
                    api.send_message(chat_id, f"✅ Объявление <b>{d['ad_id']}</b> отредактировано.")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "messages_send":
                d = pend["data"]
                data = _run_account_control(["messages", "send", d["to"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ SMS отправлено на «{_esc_tg(d['to'])}».")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "ig_comment_reply":
                d = pend["data"]
                data = _run_account_control(["instagram", "comment_reply", d["code"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"💬 Комментарий отправлен к <code>{d['code']}</code>: «{d['text'][:120]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "ig_follow":
                d = pend["data"]
                data = _run_account_control(["instagram", "follow", d["username"],
                                             "--action", d.get("action", "follow"), "--confirm"])
                st = data.get("status")
                if st == "ok":
                    verb = "подписался на" if d.get("action") == "follow" else "отписался от"
                    api.send_message(chat_id, f"✅ {verb} @{d['username']}")
                else:
                    api.send_message(chat_id, f"ℹ️ {data.get('error', st)}")
                return True
            if kind == "gmail_reply":
                d = pend["data"]
                data = _run_account_control(["google", "gmail_reply", d["msg_id"], d["text"], "--confirm"])
                if data.get("status") == "sent":
                    api.send_message(chat_id,
                                     f"✅ Ответ на письмо №{d['idx']} отправлен:\n📧 {data.get('subject')} → {data.get('to')}")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                return True
            if kind == "dm_send":
                d = pend["data"]
                data = _run_account_control(["instagram", "dm_send", d["thread"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено <b>{d['thread']}</b> в Direct: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "dm_new":
                d = pend["data"]
                data = _run_account_control(["instagram", "dm_new", d["username"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено @{d['username']}: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "viber_send":
                d = pend["data"]
                data = _run_account_control(["viber", "send", d["chat"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено в Viber <b>{d['chat']}</b>: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "android_open_app":
                d = pend["data"]
                data = _m()._android_gateway_run(["open", d["package"], "--confirm"])
                if data.get("status") == "ok":
                    api.send_message(chat_id, f"✅ На телефоне открыт <code>{_esc_tg(d['package'])}</code>.")
                else:
                    api.send_message(chat_id, f"⚠️ Android: {_esc_tg(data.get('error') or data.get('status') or '?')}")
                return True
            if kind == "android_location":
                data = _m()._android_gateway_run(["location", "--confirm"])
                if data.get("status") == "ok":
                    api.send_message(chat_id,
                                     "📍 <b>Геолокация телефона</b>\n"
                                     f"{data.get('latitude')}, {data.get('longitude')}\n"
                                     f"Точность: {data.get('accuracy_m', '—')} м")
                else:
                    api.send_message(chat_id, f"⚠️ Геолокация недоступна: {_esc_tg(data.get('error') or data.get('status') or '?')}")
                return True
            if kind == "android_pull_file":
                d = pend["data"]
                data = _m()._android_gateway_run(["pull", d["path"], "--confirm"], timeout=150)
                if data.get("status") == "ok" and data.get("file"):
                    api.send_document(chat_id, data["file"], caption="📱 Файл с Android")
                else:
                    api.send_message(chat_id, f"⚠️ Не удалось скачать файл: {_esc_tg(data.get('error') or data.get('status') or '?')}")
                return True
            if kind == "signal_send":
                d = pend["data"]
                data = _run_account_control(["signal", "send", d["chat"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено в Signal <b>{d['chat']}</b>: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "messenger_send":
                d = pend["data"]
                data = _run_account_control(["facebook", "messenger_send", d["chat"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено в Messenger <b>{d['chat']}</b>: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "tg_send":
                d = pend["data"]
                data = _run_account_control(["tg", "send", d["ref"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено в Telegram <b>{d['ref']}</b>: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "tg_bot":
                d = pend["data"]
                data = _run_account_control(["tg", "bot", d["bot"], d["command"], "--confirm"])
                st = data.get("status")
                if st == "ok":
                    reply = data.get("reply") or []
                    txt = f"🤖 <b>@{d['bot']}</b> ответил:\n" + "\n".join(
                        f"{'🤖' if not x.get('out') else '🙋'} {_esc_tg(x.get('text', ''))}" for x in reply[:3])
                    api.send_message(chat_id, txt)
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "tiktok_upload":
                d = pend["data"]
                data = _run_account_control(["tiktok", "upload", d["video"],
                                             "--caption", d.get("caption", ""), "--confirm"])
                st = data.get("status")
                if st == "published":
                    api.send_message(chat_id, "🎵 Видео опубликовано в TikTok!")
                elif st == "draft":
                    api.send_message(chat_id, f"⚠️ {data.get('note', 'загружено, но не опубликовано')}")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            api.send_message(chat_id, "❌ Неизвестный тип действия.")
            return True

    # Workflow readiness, jobs, inventory, metrics, bank monitor, recovery, reports and leads precede broad CRM words.
    if _m()._handle_treasury_intent(api, chat_id, text):
        return True
    if _m()._handle_freelance_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_brain_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_workflow_readiness_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_jobs_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_inventory_intent(api, chat_id, text):
        return True
    # Каталог склада (v22.1): «склад», «каталог», «что на складе»
    try:
        from tg_bot.catalog import _handle_catalog_intent as _hci
        if _hci(api, chat_id, text):
            return True
    except Exception:
        pass
    # Дизайн каталога (v22.2): «дизайн», «превью» — скриншот из Google Stitch
    try:
        from tg_bot.catalog import _handle_catalog_design_intent as _hcdi
        if _hcdi(api, chat_id, text):
            return True
    except Exception:
        pass
    if _m()._handle_phone_metrics_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_bank_monitor_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_recovery_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_weekly_report_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_control_center_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_audit_intent(api, chat_id, text):
        return True
    if _m()._handle_phone_lead_intent(api, chat_id, text):
        return True

    # Продажи с ТТН должны обрабатываться раньше широких regex-ов аккаунтов,
    # автопланировщика и свободного LLM-чата.
    if _m()._handle_sales_lifecycle_intent(api, chat_id, text):
        return True

    # Инбокс имеет приоритет над широким детектором Direct: слова «сообщения»
    # и «прочитанные» не должны неожиданно открывать Instagram.
    if _m()._handle_unified_inbox_intent(api, chat_id, text):
        return True

    # Dedicated app workflows must run before the generic Android intent.
    if _m()._handle_android_phone_workflow_intent(api, chat_id, text):
        return True

    if _m()._handle_android_gateway_intent(api, chat_id, text):
        return True

    ig_words = ("инста", "instagram", "подписчик", "мой профиль в инст", "мой инст",
                "мои посты", "профиль инстаграм", "мой instagram", "сторис", "story",
                "лайк", "like", "подпиш", "отпиш", "подпис", "отпис", "follow",
                "unfollow", "истори", "директ", "direct", "сообщен", "переписк", "личн",
                "чат в инстаграм", "чаты в инстаграм", "чаты директ", "чаты в директ")
    g_words = ("почт", "gmail", "email", "письм", "календар", "calendar", "диск",
               "drive", "гугл", "google", "юху", "аккаунт гугл", "google аккаунт",
               "непрочитан", "кто я", "google", "событ", "расписан", "документ",
               "поиск", "найди", "недел", "файл", "скачай", "ответь", "прочитай письмо",
               "фейсбук", "facebook", "тикток", "tiktok", "олх", "olx", "объявлен",
               "контакт", "телефонная книга", "адресная книга", "пром", "prom.ua",
               "телеграм", "telegram", "в телеге", "нова пошт", "нова почт",
               "новая пошта", "nova poshta", "novaposhta", "ттн", "посилк",
               "посылк", "відділенн", "отделен")
    is_ig = any(w in t for w in ig_words)
    is_g = any(w in t for w in g_words)
    # Telegram userbot (личный аккаунт)
    tg_words = any(w in t for w in ("тг ", "телеграм", "telegram", "в телеге",
                                    "личный телеграм", "мой телеграм",
                                    "боту @", "команду боту", "команда боту"))
    other_words = ("вайбер", "вибер", "viber", "signal", "сигнал", "мессенджер", "messenger",
                   "опубликуй видео", "опубликуй ролик", "опубликуй в тикток",
                   "боту @", "команду боту", "команда боту",
                   "в телеге", "телеграм", "telegram", "тг",
                   "инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений",
                   "где что новое", "проверь всё", "напомни", "напоминание",
                   "аналитик", "рост подписчик", "динамика", "статистика аккаунт",
                   "сколько прибавил", "тренд", "запланируй пост", "пост в тикток на",
                   "пост в инстаграм на", "расписание постов",
                   "озвучь инбокс", "озвучь всё", "голосом инбокс", "прочитай инбокс вслух",
                   "найди во всех", "ищи везде", "найди везде", "поиск по всем",
                   "отметь всё прочитанным", "всё прочитано", "отметь прочитанным",
                   "присылай инбокс", "пришли инбокс", "включи инбокс", "отключи инбокс",
                   "расписание инбокса",
                   "комментари", "коментар", "ответь на комментарий", "ответь в комментар",
                   "шаблон", "ответь клиенту", "быстрый ответ", "шаблоны",
                   "следи за ценой", "мониторинг цен", "цена на олх", "снизил",
                   "экспортируй", "выгрузи", "экспорт", "в excel", "в эксель",
                   "выгрузить в файл", "включи голосовые ответы", "отвечай голосом",
                   "включи голос", "выключи голосовые ответы", "отвечай текстом",
                   "выключи голос",
                   "запиши продажу", "запиши расход", "запиши трату", "продал за",
                   "купил за", "потратил", "сколько заработал", "прибыль", "финанс",
                   "учет", "учёт", "деньги за неделю", "деньги за месяц",
                   "мои операции", "операции",
                   "создай объявление", "создай объявлени", "новое объявление на олх",
                   "создай объявления", "напиши объявление",
                   "автоответ олх", "автоответ olx", "автоответ в олх",
                   "автоответ покупателям",
                   "подними объявления", "подними мои объявления", "обнови объявления",
                   "мои объявления олх", "мои объявления olx", "контроль объявлений",
                   "сколько объявлений",
                   "добавь деталь", "добавь на склад", "спиши деталь",
                   "что на складе", "склад", "найди деталь", "продал ",
                   "остатки", "инвентаризац", "сколько деталей",
                   "вечерний отчёт", "вечерний отчет", "итоги дня",
                   "отчёт за день", "отчет за день", "дневной отчёт",
                   "сделай объявление из фото", "объявление по фото", "фото в объявление",
                   "выложи по фото", "деталь по фото",
                   "создай гугл таблицу", "создай google таблицу", "в гугл таблицу",
                   "создай таблицу из финансов", "создай таблицу из склада",
                   "сколько стоит", "почём", "цена на", "что стоит",
                   "распознай деталь", "что за деталь", "определи деталь",
                   "оцени деталь", "узнай деталь",
                   "кто продаёт дешевле", "кто продает дешевле", "где дешевле",
                   "топ выгодных", "лучшая цена",
                   "месячный отчёт", "месячный отчет", "отчёт за месяц",
                   "отчет за месяц", "отчёт за 30 дней", "сводка за месяц",
                   "подтверди телефон олх", "подтверди телефон olx", "подтвердить телефон олх",
                   "подтверждение телефона олх", "опубликуй это объявление",
                   "опубликуй объявление на олх", "публикуй на олх", "создай на олх",
                   "выложи на олх",
                   "удали объявление", "удалить объявление", "сними объявление",
                   "отредактируй объявление", "редактируй объявление", "измени объявление",
                   "обнови объявление", "мои объявления", "список объявлений")
    is_other = any(w in t for w in other_words)
    generic_dm_request = (
        "чат" in t
        and any(word in t for word in ("покажи", "прочитай", "последние", "новые"))
        and not tg_words
        and not any(word in t for word in ("whatsapp", "ватсап", "вайбер", "viber", "signal", "мессенджер"))
    )
    if generic_dm_request:
        is_ig = True
    if not is_ig and not is_g and not is_other and not tg_words:
        return False

    # ---- Instagram ----
    if is_ig and not tg_words:
        # ---- Direct (переписка) ----
        # «чат» без уточнения — DM только если речь не про Telegram
        is_dm = any(w in t for w in ("директ", "direct", "сообщен", "переписк",
                                     "чат в інст", "чат в инст", "личн")) or \
                ("чат" in t and "телеге" not in t and "телеграм" not in t
                 and "telegram" not in t and "тг" not in t)
        if is_dm:
            send_word = any(w in t for w in ("напиши", "отправь", "ответь", "написать",
                                             "reply", "напишіть", "відповісти"))
            read_word = any(w in t for w in ("прочитай", "покажи", "что в", "що в",
                                             "последние", "новые", "прочитать"))
            if send_word:
                body = ""
                target = ""
                m_colon = re.search(r":\s*(.+)$", text, re.IGNORECASE)
                if m_colon:
                    target = text[:m_colon.start()]
                    body = m_colon.group(1).strip()
                else:
                    rest = re.sub(
                        r"^(напиши|отправь|ответь|написать|скажи|напишіть|відповісти)"
                        r"(\s+(в|в\s+директ|директ|direct|личку|сообщение))?\s+",
                        "", text, flags=re.IGNORECASE)
                    rest = re.sub(r"^(в|в\s+директ|директ|direct|личку|сообщение)\s+",
                                  "", rest, flags=re.IGNORECASE)
                    parts = rest.split(None, 1)
                    if parts:
                        target = parts[0].strip(" ,.;:—–")
                        body = parts[1].strip() if len(parts) > 1 else ""
                target = re.sub(r"^(в|ответить|написать|сообщение|директ|direct)\s*",
                                "", target, flags=re.IGNORECASE).strip(" ,.;:—–")
                if not target or not body:
                    api.send_message(chat_id,
                                     "💬 <b>Директ</b>: напишите, например:\n"
                                     "«напиши в директ Серега: привет, как дела?»\n"
                                     "или «ответь в директ @username, текст»")
                    return True
                if target.startswith("@"):
                    _pending_confirm[chat_id] = {"kind": "dm_new",
                                                 "data": {"username": target.lstrip("@"),
                                                          "text": body}}
                    api.send_message(chat_id,
                                     f"💬 Новый чат с <b>@{target.lstrip('@')}</b>:\n"
                                     f"«{body[:200]}»\n\nПодтвердите: «да» / «нет»")
                else:
                    _pending_confirm[chat_id] = {"kind": "dm_send",
                                                 "data": {"thread": target, "text": body}}
                    api.send_message(chat_id,
                                     f"💬 Отправить <b>{target}</b> в Direct:\n"
                                     f"«{body[:200]}»\n\nПодтвердите: «да» / «нет»")
                return True
            if read_word:
                name = None
                m = re.search(r"(?:директ|чат|чате|чату|переписке|переписку|сообщениях)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)",
                              text, re.IGNORECASE)
                if m:
                    cand = m.group(1).strip()
                    cand = re.sub(r"^(в|от|с|у|мне|мой|моем|новые|последние|прочитай|покажи)\s+", "", cand,
                                  flags=re.IGNORECASE).strip()
                    if len(cand) >= 2:
                        name = cand
                api.send_message(chat_id, "⏳ Открываю Direct…")
                data = _run_account_control(["instagram", "dm_read", name or "Серега Потуроев",
                                             "--limit", "12"])
                if data.get("status") == "ok":
                    msgs = data.get("messages") or []
                    if not msgs:
                        api.send_message(chat_id, "💬 В чате нет текстовых сообщений (только системные).")
                    else:
                        txt = "💬 <b>Последние сообщения</b>:\n" + "\n".join(
                            f"• {_esc_tg(m.get('text', ''))}" for m in msgs[-12:])
                        api.send_message(chat_id, txt)
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                return True
            # просто «директ» — список чатов
            api.send_message(chat_id, "⏳ Загружаю Direct…")
            data = _run_account_control(["instagram", "dm_list", "10"])
            if data.get("status") == "ok":
                threads = data.get("threads") or []
                if not threads:
                    api.send_message(chat_id, "💬 В Direct пусто.")
                else:
                    txt = "💬 <b>Чаты Direct</b>:\n" + "\n".join(
                        f"• <b>{_esc_tg(x.get('name', '?'))}</b> — {_esc_tg(x.get('preview', ''))}"
                        for x in threads)
                    api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        if any(w in t for w in ("сторис", "story", "истори")):
            api.send_message(chat_id,
                             "📤 <b>Сторис</b>: к сожалению, Instagram web не даёт создавать сторис "
                             "из браузера (проверено: кнопки «Create»/Story нет ни в desktop, ни в "
                             "mobile-версии). Сторис можно сделать только в мобильном приложении. "
                             "А вот лайки, подписки, посты — легко!")
            return True
        if any(w in t for w in ("лайк", "like")):
            urls = re.findall(r"https?://\S+", text) or re.findall(r"/p/[A-Za-z0-9_-]+", text)
            if not urls:
                api.send_message(chat_id,
                                 "❤️ <b>Лайк</b>: пришлите ссылку на пост, например:\n"
                                 "«лайкни https://www.instagram.com/p/CODE/»")
                return True
            url = urls[0] if urls[0].startswith("http") else f"https://www.instagram.com{urls[0]}"
            data = _run_account_control(["instagram", "like", url])
            st = data.get("status")
            if st == "already_liked":
                api.send_message(chat_id, "👍 Пост уже лайкнут.")
                return True
            if st == "need_confirm":
                _pending_confirm[chat_id] = {"kind": "ig_like", "data": {"url": url}}
                api.send_message(chat_id, f"❤️ Поставить лайк: {url}\nПодтвердите: «да» / «нет»")
                return True
            api.send_message(chat_id, f"❌ {data.get('error', st)}")
            return True
        if ("подпиши" in t or "отпиши" in t):
            action = "unfollow" if "отпиши" in t else "follow"
            m = re.search(r"@([a-zA-Z0-9_.]+)", text)
            uname = m.group(1) if m else None
            if not uname:
                for w in reversed(re.split(r"[\s,]+", t)):
                    w = w.strip("@")
                    if w and not any(k in w for k in ("подпиши", "отпиши", "подпишись", "отпишись",
                                                      "на", "от", "меня", "пожалуйста", "себя",
                                                      "надо", "нужно", "подпис", "отпис", "аккаунт")):
                        uname = w
                        break
            if not uname:
                api.send_message(chat_id,
                                 "👤 <b>Подписка</b>: укажите username, например\n"
                                 "«подпишись на @dawnrichard» или «отпишись от @ivan»")
                return True
            data = _run_account_control(["instagram", "follow", uname, "--action", action])
            st = data.get("status")
            if st in ("already_following", "not_following"):
                api.send_message(chat_id, f"ℹ️ @{uname}: {data.get('button', st)}")
                return True
            if st == "need_confirm":
                _pending_confirm[chat_id] = {"kind": "ig_follow",
                                             "data": {"username": uname, "action": action}}
                verb = "подписаться на" if action == "follow" else "отписаться от"
                api.send_message(chat_id, f"👤 {verb} @{uname}?\nПодтвердите: «да» / «нет»")
                return True
            api.send_message(chat_id, f"ℹ️ {data.get('error', st)}")
            return True
        if any(w in t for w in ("скрин", "покажи", "фото")):
            _acct_instagram(api, chat_id, "screenshot")
            return True
        if "пост" in t and "/p/" in text:
            m = re.search(r"/p/([A-Za-z0-9_-]+)", text)
            if m:
                data = _run_account_control(["instagram", "post", m.group(1)])
                if data.get("status") == "ok":
                    p = data.get("post", {})
                    txt = (f"🖼 <b>Пост {p.get('code')}</b>\n"
                           f"💬 {p.get('caption') or 'без подписи'}\n"
                           f"❤️ Лайки: {p.get('likes') or '?'}\n"
                           f"🔗 {p.get('url')}")
                    _acct_send_result(api, chat_id,
                                      {"status": "ok", "text": txt,
                                       "screenshot": data.get("screenshot"),
                                       "caption": "🖼 Пост"}, "")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                return True
        if any(w in t for w in ("пост", "посты", "публикац")):
            _acct_instagram(api, chat_id, "posts")
            return True
        # профиль / статистика / «покажи инсту» / «мой инст»
        _acct_instagram(api, chat_id, "profile")
        return True

    # ---- Дайджест / сводка ----
    if any(w in t for w in ("дайджест", "утренний отчёт", "утренний отчет", "что нового",
                            "сводка", "сводку", "отчёт за день", "отчет за день",
                            "сводку за день", "итоги дня")):
        api.send_message(chat_id, "⏳ Собираю дайджест (почта + календарь + Instagram)…")
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
        return True

    # ---- Планировщик постов ----
    if any(w in t for w in ("запланируй пост", "запланupyй пост", "пост в тикток на",
                            "пост в инстаграм на", "расписание постов")):
        platform = "tiktok" if "тикток" in t or "tiktok" in t else \
                   ("instagram" if "инстаграм" in t or "instagram" in t or "инст" in t else "tiktok")
        m_time = re.search(r"\b(\d{1,2})[:.](\d{2})\b", t)
        if not m_time:
            api.send_message(chat_id, "📅 Формат: «запланируй пост в тикток завтра в 18:00 описание»")
            return True
        hh, mm = int(m_time.group(1)), int(m_time.group(2))
        day_off = 1 if "завтра" in t else (2 if "послезавтра" in t else 0)
        target = datetime.now() + timedelta(days=day_off)
        target = target.replace(hour=hh, minute=mm, second=0, microsecond=0)
        text = re.sub(r"^(запланируй пост|пост)\s*(в\s+)?(тикток|tiktok|инстаграм|instagram|инст)?\s*(на)?\s*", "", t, flags=re.IGNORECASE)
        text = re.sub(r"\b\d{1,2}[:.]\d{2}\b", "", text).strip()
        text = re.sub(r"^(завтра|сегодня|послезавтра)\s*", "", text, flags=re.IGNORECASE).strip()
        video = _last_video.get(chat_id, "")
        # очередь
        qfile = PROJECT_ROOT / "data" / "posts_queue.json"
        try:
            q = json.loads(qfile.read_text(encoding="utf-8"))
        except Exception:
            q = []
        q.append({"platform": platform, "at": target.isoformat(), "text": text,
                  "chat_id": chat_id, "video": video})
        qfile.parent.mkdir(parents=True, exist_ok=True)
        qfile.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
        api.send_message(chat_id,
                         f"📅 Запланировано: {platform} {target.strftime('%d.%m %H:%M')}\n"
                         f"«{text[:100]}»\n"
                         f"{'🎬 Видео приложено — опубликуется автоматически' if video and platform == 'tiktok' else 'ℹ️ Придёт напоминание (видео не приложено или не TikTok)'}")
        return True

    # ---- Instagram комментарии ----
    if any(w in t for w in ("комментари", "коментар", "отзывы под постом", "ответь на комментарий",
                            "ответь в комментар")):
        m_code = re.search(r"/p/([A-Za-z0-9_-]+)|пост\s*([A-Za-z0-9_-]{6,})", text)
        code = (m_code.group(1) or m_code.group(2)) if m_code else None
        if not code:
            api.send_message(chat_id,
                             "💬 <b>Комментарии</b>: пришлите ссылку на пост, например\n"
                             "«покажи комментарии к /p/CODE/»\n"
                             "или «ответь на комментарий в /p/CODE/: текст»")
            return True
        if any(w in t for w in ("ответь на комментарий", "ответь в комментар")):
            m_body = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m_body.group(1).strip() if m_body else ""
            if not body:
                api.send_message(chat_id, "💬 Напишите текст ответа после двоеточия.")
                return True
            _pending_confirm[chat_id] = {"kind": "ig_comment_reply",
                                         "data": {"code": code, "text": body}}
            api.send_message(chat_id,
                             f"💬 Ответить на комментарий к <code>{code}</code>:\n"
                             f"«{body[:150]}»\n\nОтправить? «да» / «нет»")
            return True
        api.send_message(chat_id, "⏳ Читаю комментарии…")
        data = _run_account_control(["instagram", "comments", code, "--limit", "10"])
        if data.get("status") == "ok":
            com = data.get("comments") or []
            if not com:
                api.send_message(chat_id, f"💬 У поста <code>{code}</code> комментариев нет.")
            else:
                txt = f"💬 <b>Комментарии к /p/{code}/</b>:\n" + "\n".join(
                    f"• {_esc_tg(c.get('text', ''))[:120]}" for c in com[:10])
                api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Шаблоны ответов клиентам ----
    if any(w in t for w in ("шаблон", "ответь клиенту", "быстрый ответ", "шаблоны")):
        if "добавь шаблон" in t or "сохрани шаблон" in t or "новый шаблон" in t:
            m = re.search(r"(?:добавь|сохрани|новый)\s+шаблон\s+([^:]+):\s*(.+)", text, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                body = m.group(2).strip()
                tpl = _m()._load_templates()
                tpl[name] = body
                _m()._save_templates(tpl)
                api.send_message(chat_id, f"📝 Шаблон <b>{name}</b> сохранён: «{body[:80]}»")
            else:
                api.send_message(chat_id, "📝 Формат: «добавь шаблон гарантия: Здравствуйте! Да, гарантия 14 дней»")
            return True
        tpl = _m()._load_templates()
        if "шаблоны" in t and not tpl:
            api.send_message(chat_id, "📝 Шаблонов пока нет. «добавь шаблон &lt;имя&gt;: &lt;текст&gt;»")
            return True
        # «ответь клиенту <шаблон>» — вставить шаблон в ответ
        m_use = re.search(r"(?:ответь клиенту|по шаблону|используй шаблон)\s*[\"«']?([\w\s-]+)[\"»']?", text, re.IGNORECASE)
        if m_use:
            name = m_use.group(1).strip().lower()
            found = None
            for k, v in tpl.items():
                if k.lower() == name:
                    found = v
                    break
            if not found:
                # частичное совпадение
                for k, v in tpl.items():
                    if name in k.lower() or k.lower() in name:
                        found = v
                        break
            if found:
                api.send_message(chat_id, f"📝 Шаблон <b>{name}</b>:\n«{found}»\n\n"
                                          f"Куда отправить? «отправь клиенту в директ …» или укажите канал.")
            else:
                api.send_message(chat_id, "📝 Такого шаблона нет. Доступны: " + ", ".join(tpl.keys()))
            return True
        if tpl:
            api.send_message(chat_id, "📝 <b>Шаблоны:</b>\n" + "\n".join(
                f"• <b>{_esc_tg(k)}</b>: {_esc_tg(v)[:60]}" for k, v in tpl.items()) +
                "\n\n«ответь клиенту <имя шаблона>» — показать текст")
        return True

    # ---- TikTok upload ----
    if any(w in t for w in ("опубликуй видео", "опубликуй ролик", "загрузи видео в тикток",
                            "пости видео в тикток", "опубликуй в тикток")):
        caption = re.sub(r"(опубликуй видео|опубликуй ролик|загрузи видео в тикток|пости видео в тикток|опубликуй в тикток)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        video = _last_video.get(chat_id)
        if not video:
            api.send_message(chat_id,
                             "🎬 Отправьте видео сюда, а потом напишите «опубликуй видео в тикток <описание>».")
            return True
        if not os.path.exists(video):
            api.send_message(chat_id, "❌ Сохранённое видео не найдено. Пришлите видео заново.")
            return True
        _pending_confirm[chat_id] = {"kind": "tiktok_upload",
                                     "data": {"video": video, "caption": caption}}
        api.send_message(chat_id,
                         f"🎬 <b>Публикация в TikTok</b>\n"
                         f"Файл: {os.path.basename(video)}\n"
                         f"Описание: «{caption[:200] or '—'}»\n\n"
                         f"Опубликовать? «да» / «нет» (риск: TikTok может запросить проверку)")
        return True

    # ---- Viber (десктоп) ----
    if any(w in t for w in ("вайбер", "вибер", "viber")) and not any(
            w in t for w in ("инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений")):
        # Непрочитанные сообщения Viber с телефона (активные уведомления)
        _unread_hint = any(w in t for w in ("непрочитанн", "сообщен", "собери", "посмотри",
                                            "проверь", "что ново", "новые", "пришли", "пришло"))
        _send_hint = any(w in t for w in ("напиши", "отправь", "написать", "ответь", "перешли"))
        if _unread_hint and not _send_hint:
            import subprocess as _sp_vib
            try:
                r = _sp_vib.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_viber_unread.py")],
                                capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
                out = (r.stdout or r.stderr or "").strip()
                api.send_message(chat_id, out[:3900] if out else "💜 Не удалось собрать Viber.")
            except Exception as exc_vib:
                api.send_message(chat_id, f"❌ Viber: {_esc_tg(str(exc_vib)[:180])}")
            return True
        if "чернов" in t or "draft" in t:
            try:
                from viber_drafts import ViberDraftStore
                drafts = ViberDraftStore(PROJECT_ROOT).pending(12)
                if not drafts:
                    api.send_message(chat_id, "💜 Ожидающих Viber-черновиков нет.")
                else:
                    lines = ["💜 <b>Черновики Viber:</b>"]
                    for draft in drafts:
                        lines.append(f"• <b>{_esc_tg(draft.get('contact'))}</b>: «{_esc_tg(str(draft.get('text') or '')[:150])}»")
                    lines.append("\nДля отправки используйте кнопку под уведомлением-черновиком.")
                    api.send_message(chat_id, "\n".join(lines)[:3900])
            except Exception as exc:
                api.send_message(chat_id, f"⚠️ Не удалось прочитать черновики Viber: {_esc_tg(str(exc))[:180]}")
            return True
        send_word = any(w in t for w in ("напиши", "отправь", "написать", "ответь"))
        read_word = any(w in t for w in ("прочитай", "покажи", "что в", "последние"))
        if send_word:
            m = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m.group(1).strip() if m else ""
            target = re.sub(r"^(напиши|отправь|написать|ответь)(\s+(в|в\s+вайбер|вайбер|viber|вибер))?\s+", "",
                            text, flags=re.IGNORECASE)
            target = re.sub(r"^(в|вайбер|viber|вибер)\s+", "", target, flags=re.IGNORECASE)
            target = target.split(":", 1)[0].strip(" ,.;:—–")
            if not target or not body:
                api.send_message(chat_id,
                                 "💬 <b>Viber</b>: напишите «напиши в вайбер &lt;имя&gt;: &lt;текст&gt;»")
                return True
            _pending_confirm[chat_id] = {"kind": "viber_send",
                                         "data": {"chat": target, "text": body}}
            api.send_message(chat_id,
                             f"💬 Отправить <b>{target}</b> в Viber:\n«{body[:200]}»\n\n«да» / «нет»")
            return True
        if read_word:
            m = re.search(r"(?:вайбер|viber|вибер)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)", text, re.IGNORECASE)
            chat = m.group(1).strip() if m else ""
            api.send_message(chat_id, "⏳ Открываю Viber…")
            data = _run_account_control(["viber", "read", chat or "Viber"])
            if data.get("status") == "ok":
                msgs = data.get("messages") or []
                if not msgs:
                    api.send_message(chat_id, "💬 В чате нет распознанных сообщений (или пусто).")
                else:
                    api.send_message(chat_id, "💬 <b>Viber</b>:\n" + "\n".join(
                        f"• {_esc_tg(x.get('text', ''))}" for x in msgs[-12:]))
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        # список чатов
        api.send_message(chat_id, "⏳ Читаю чаты Viber…")
        data = _run_account_control(["viber", "chats"])
        if data.get("status") == "ok":
            chats = data.get("chats") or []
            if chats:
                api.send_message(chat_id, "💬 <b>Чаты Viber</b>:\n" + "\n".join(
                    f"• {_esc_tg(c.get('name'))}" for c in chats[:20]))
            else:
                api.send_message(chat_id,
                                 "💬 Не нашёл чаты (возможно, Viber не залогинен — нужен QR-вход).")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Signal (десктоп) ----
    if any(w in t for w in ("signal", "сигнал")) and not any(
            w in t for w in ("инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений")):
        if "чернов" in t or "draft" in t:
            try:
                from signal_drafts import SignalDraftStore
                drafts = SignalDraftStore(PROJECT_ROOT).pending(12)
                if not drafts:
                    api.send_message(chat_id, "🔒 Ожидающих Signal-черновиков нет.")
                else:
                    lines = ["🔒 <b>Черновики Signal:</b>"]
                    for draft in drafts:
                        lines.append(f"• <b>{_esc_tg(draft.get('contact'))}</b>: «{_esc_tg(str(draft.get('text') or '')[:150])}»")
                    lines.append("\nДля отправки используйте кнопку под уведомлением-черновиком.")
                    api.send_message(chat_id, "\n".join(lines)[:3900])
            except Exception as exc:
                api.send_message(chat_id, f"⚠️ Не удалось прочитать черновики Signal: {_esc_tg(str(exc))[:180]}")
            return True
        send_word = any(w in t for w in ("напиши", "отправь", "написать", "ответь"))
        read_word = any(w in t for w in ("прочитай", "покажи", "что в", "последние"))
        if send_word:
            m = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m.group(1).strip() if m else ""
            target = re.sub(r"^(напиши|отправь|написать|ответь)(\s+(в|в\s+signal|signal|в\s+сигнал|сигнал))?\s+", "",
                            text, flags=re.IGNORECASE)
            target = re.sub(r"^(в|signal|сигнал)\s+", "", target, flags=re.IGNORECASE)
            target = target.split(":", 1)[0].strip(" ,.;:—–")
            if not target or not body:
                api.send_message(chat_id,
                                 "🔒 <b>Signal</b>: напишите «напиши в Signal &lt;имя&gt;: &lt;текст&gt;»")
                return True
            _pending_confirm[chat_id] = {"kind": "signal_send",
                                         "data": {"chat": target, "text": body}}
            api.send_message(chat_id,
                             f"🔒 Отправить <b>{target}</b> в Signal:\n«{body[:200]}»\n\n«да» / «нет»")
            return True
        if read_word:
            m = re.search(r"(?:signal|сигнал)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)", text, re.IGNORECASE)
            chat = m.group(1).strip() if m else ""
            api.send_message(chat_id, "⏳ Открываю Signal…")
            data = _run_account_control(["signal", "read", chat or "Signal", "--limit", "12"])
            if data.get("status") == "ok":
                msgs = data.get("messages") or []
                if not msgs:
                    api.send_message(chat_id, "🔒 В чате нет распознанных сообщений (или пусто).")
                else:
                    api.send_message(chat_id, "🔒 <b>Signal</b>:\n" + "\n".join(
                        f"• {_esc_tg(x.get('text', ''))}" for x in msgs[-12:]))
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        api.send_message(chat_id, "⏳ Читаю чаты Signal…")
        data = _run_account_control(["signal", "chats"])
        if data.get("status") == "ok":
            chats = data.get("chats") or []
            if chats:
                api.send_message(chat_id, "🔒 <b>Чаты Signal</b>:\n" + "\n".join(
                    f"• {_esc_tg(c.get('name'))}" for c in chats[:20]))
            else:
                api.send_message(chat_id,
                                 "🔒 Не нашёл чаты Signal (возможно, нужен повторный QR-вход).")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Messenger ----
    if any(w in t for w in ("мессенджер", "messenger", "фейсбук чат", "чат фейсбук")):
        send_word = any(w in t for w in ("напиши", "отправь", "написать", "ответь"))
        read_word = any(w in t for w in ("прочитай", "покажи", "что в", "последние"))
        if send_word:
            m = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m.group(1).strip() if m else ""
            target = re.sub(r"^(напиши|отправь|написать|ответь)(\s+(в|в\s+мессенджер|мессенджер|messenger))?\s+", "",
                            text, flags=re.IGNORECASE)
            target = re.sub(r"^(в|мессенджер|messenger)\s+", "", target, flags=re.IGNORECASE)
            target = target.split(":", 1)[0].strip(" ,.;:—–")
            if not target or not body:
                api.send_message(chat_id,
                                 "💬 <b>Messenger</b>: напишите «напиши в мессенджер &lt;имя&gt;: &lt;текст&gt;»")
                return True
            _pending_confirm[chat_id] = {"kind": "messenger_send",
                                         "data": {"chat": target, "text": body}}
            api.send_message(chat_id,
                             f"💬 Отправить <b>{target}</b> в Messenger:\n«{body[:200]}»\n\n«да» / «нет»")
            return True
        if read_word:
            m = re.search(r"(?:мессенджер|messenger)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)", text, re.IGNORECASE)
            chat = m.group(1).strip() if m else ""
            api.send_message(chat_id, "⏳ Открываю Messenger…")
            data = _run_account_control(["facebook", "messenger_read", chat or "Chat", "--limit", "12"])
            if data.get("status") == "ok":
                msgs = data.get("messages") or []
                if not msgs:
                    api.send_message(chat_id, "💬 В чате нет сообщений.")
                else:
                    api.send_message(chat_id, "💬 <b>Messenger</b>:\n" + "\n".join(
                        f"• {_esc_tg(x.get('text', ''))}" for x in msgs[-12:]))
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        api.send_message(chat_id, "⏳ Загружаю чаты Messenger…")
        data = _run_account_control(["facebook", "messenger_list", "--limit", "10"])
        if data.get("status") == "ok":
            chats = data.get("chats") or []
            if chats:
                api.send_message(chat_id, "💬 <b>Чаты Messenger</b>:\n" + "\n".join(
                    f"• {_esc_tg(c.get('name'))}" for c in chats[:10]))
            else:
                api.send_message(chat_id, "💬 Чатов не нашёл.")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Facebook ----
    if any(w in t for w in ("фейсбук", "facebook", "фб", "fb ")) and not any(w in t for w in ("директ", "сообщен")):
        if any(w in t for w in ("лента", "новости", "новости", "посты", "пост", "feed")):
            api.send_message(chat_id, "⏳ Открываю ленту Facebook…")
            data = _run_account_control(["facebook", "feed", "5"])
            if data.get("status") == "ok":
                feed = data.get("feed") or []
                if feed:
                    txt = "📰 <b>Лента Facebook</b>:\n\n" + "\n\n".join(
                        f"• {_esc_tg(x.get('text', ''))[:300]}" for x in feed[:5])
                    api.send_message(chat_id, txt)
                else:
                    api.send_message(chat_id, "📰 Лента пуста (не удалось распарсить).")
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        else:
            api.send_message(chat_id, "⏳ Захожу в Facebook…")
            data = _run_account_control(["facebook", "profile"])
            if data.get("status") == "ok":
                f = data.get("facebook", {})
                txt = (f"📘 <b>Facebook</b>\n"
                       f"👤 Имя: {_esc_tg(f.get('name'))}\n"
                       f"🔗 {f.get('profile_url')}\n"
                       f"🔔 Уведомлений: {f.get('notifications') or 0}")
                _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                 "screenshot": f.get("screenshot"),
                                                 "caption": "📘 Facebook"}, "")
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- TikTok ----
    if any(w in t for w in ("тикток", "tiktok", "тик ток", "тт ")):
        api.send_message(chat_id, "⏳ Захожу в TikTok…")
        data = _run_account_control(["tiktok", "profile"])
        if data.get("status") == "ok":
            p = data.get("tiktok", {})
            txt = (f"🎵 <b>TikTok</b>\n"
                   f"👤 Имя: {_esc_tg(p.get('name') or p.get('username'))}\n"
                   f"👥 Подписчики: {p.get('followers') or 0}\n"
                   f"🔄 Подписки: {p.get('following') or 0}\n"
                   f"❤️ Лайки: {p.get('likes') or 0}\n"
                   f"ℹ️ {_esc_tg(p.get('bio') or 'без описания')}\n"
                   f"🔗 {p.get('profile_url')}")
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": p.get("screenshot"),
                                             "caption": "🎵 TikTok"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Аналитика ----
    if any(w in t for w in ("аналитик", "рост подписчик", "динамика", "статистика аккаунт",
                            "сколько прибавил", "тренд")):
        api.send_message(chat_id, "⏳ Собираю аналитику (IG, TikTok, OLX)…")
        import subprocess as _sp
        # обновить снапшот прямо сейчас
        try:
            _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_analytics_snapshot.py")],
                    capture_output=True, text=True, timeout=240, cwd=str(PROJECT_ROOT))
        except Exception:
            pass
        # читаем историю
        hist = {}
        try:
            hist = json.loads((PROJECT_ROOT / "data" / "analytics_state.json").read_text(encoding="utf-8"))
        except Exception:
            pass
        if not hist:
            api.send_message(chat_id, "📊 Нет данных аналитики ещё. Соберу при следующем прогоне.")
            return True
        dates = sorted(hist.keys())
        today = dates[-1]
        cur = hist[today]
        # ищем точку 7 и 30 дней назад
        def _delta(key):
            vals = []
            for d in reversed(dates):
                v = hist[d].get(key)
                if v is not None:
                    vals.append((d, v))
            cur_v = cur.get(key)
            if not vals or cur_v is None:
                return None, None, None
            # первая запись не раньше, чем сегодня
            base = vals[-1] if len(vals) > 1 else vals[0]
            return cur_v, base[1], len(vals) - 1

        txt = [f"📊 <b>Аналитика на {today}</b>"]
        for label, key in (("👥 Instagram подписчики", "instagram_followers"),
                           ("🔄 Instagram подписки", "instagram_following"),
                           ("🎵 TikTok подписчики", "tiktok_followers"),
                           ("❤️ TikTok лайки", "tiktok_likes"),
                           ("🛒 OLX объявления", "olx_ads")):
            cur_v, base_v, n = _delta(key)
            if cur_v is None:
                continue
            line = f"{label}: <b>{cur_v}</b>"
            if base_v is not None and n and base_v != cur_v:
                d = cur_v - base_v
                arrow = "📈" if d > 0 else "📉"
                line += f" {arrow}{d:+d} (за {n} дн.)"
            txt.append(line)
        api.send_message(chat_id, "\n".join(txt))
        return True

    # ---- Расписание инбокса ----
    if re.match(r"^(присылай|пришли|включи|отключи|выключи|убери)\s+инбокс", t) or \
       re.match(r"^(включи|отключи)\s+расписание\s+инбокса", t):
        _inbox_schedule_cmd(api, chat_id, text)
        return True

    # ---- Экспорт данных ----
    if any(w in t for w in ("экспортируй", "выгрузи", "экспорт", "в excel", "в эксель",
                            "выгрузить в файл")):
        import subprocess as _sp
        if "почт" in t or "gmail" in t or "письм" in t:
            api.send_message(chat_id, "⏳ Экспортирую почту в Excel…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), "gmail", "50"],
                        capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        elif "контакт" in t:
            api.send_message(chat_id, "⏳ Экспортирую контакты в Excel…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), "contacts", "200"],
                        capture_output=True, text=True, timeout=170, cwd=str(PROJECT_ROOT))
        elif "финанс" in t or "продаж" in t or "склад" in t or "детал" in t:
            what = "finance" if "финанс" in t or "продаж" in t else "inventory"
            api.send_message(chat_id, f"⏳ Экспортирую {'финансы' if what == 'finance' else 'склад'} в CSV (для Google Таблиц)…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), what],
                        capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        else:  # olx
            q = re.sub(r"(экспортируй|выгрузи|экспорт|объявления)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            q = q.replace("олх", "").replace("olx", "").strip(" ,.;:—–")
            api.send_message(chat_id, f"⏳ Экспортирую объявления OLX{' «' + q + '»' if q else ''} в Excel…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), "olx"] + ([q] if q else []),
                        capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        try:
            out = (r.stdout or "").strip()
            start = out.find("{")
            res = json.loads(out[start:]) if start >= 0 else {"error": out[-200:]}
        except Exception:
            res = {"error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok" and res.get("file") and os.path.exists(res["file"]):
            try:
                api.send_document(chat_id, res["file"], caption=f"📑 Экспорт ({res.get('rows', '?')} строк)")
            except Exception as e:
                api.send_message(chat_id, f"✅ Файл готов: {res['file']} (не смог отправить: {e})")
        else:
            api.send_message(chat_id, f"❌ Экспорт не удался: {res.get('error', '?')}")
        return True

    # ---- Распознавание фото запчасти ----
    if any(w in t for w in ("распознай деталь", "что за деталь", "определи деталь",
                            "оцени деталь", "узнай деталь", "деталь по фото")):
        photo = _last_photo.get(chat_id)
        if not photo:
            api.send_message(chat_id, "📷 Сначала пришлите фото детали, потом «распознай деталь»")
            return True
        api.send_message(chat_id, "🤖 Распознаю деталь по фото (Gemini vision)… ~30 сек")
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_photo_recognition.py"), photo],
                    capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            txt = (f"🔍 <b>Распознано:</b>\n"
                   f"🔩 Деталь: <b>{_esc_tg(res.get('part', '?'))}</b>\n"
                   f"📋 Состояние: {_esc_tg(res.get('condition') or '—')}\n"
                   f"💰 Цена: {res.get('price') or '?'} грн\n"
                   f"🚗 Совместимость: {_esc_tg(res.get('compatible') or '—')}\n"
                   f"📝 {_esc_tg(res.get('notes') or '')}\n\n"
                   f"Добавить на склад? «добавь деталь {res.get('part', '')}, 1 шт»\n"
                   f"Или «создай объявление: {res.get('part', '')}»")
            api.send_message(chat_id, txt[:3900])
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось распознать')}")
        return True

    # ---- Фото детали → черновик объявления ----
    if any(w in t for w in ("сделай объявление из фото", "объявление по фото", "фото в объявление",
                            "выложи по фото", "деталь по фото")):
        photo = _last_photo.get(chat_id)
        if not photo:
            api.send_message(chat_id, "📷 Сначала пришлите фото детали, потом «сделай объявление из фото»")
            return True
        api.send_message(chat_id, "📷 Отлично, фото получил! Опишите деталь одним сообщением, например:\n"
                                  "«фара BMW X5 ксенон 2003, цена 2000»\n— и я сгенерирую объявление.")
        _photo_pending[chat_id] = True
        return True
    if chat_id in _photo_pending and _photo_pending[chat_id]:
        # это описание детали после фото
        _photo_pending[chat_id] = False
        photo = _last_photo.get(chat_id, "")
        part = text.strip()
        import subprocess as _sp
        api.send_message(chat_id, f"⏳ Генерирую объявление по фото: «{part}»…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "gen", part],
                    capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-150:]}
        if res.get("status") == "ok":
            txt = (f"📝 <b>Объявление (по фото):</b>\n"
                   f"Заголовок: <b>{_esc_tg(res.get('title', ''))}</b>\n"
                   f"Цена: {res.get('price', '?')} грн\n\n"
                   f"Описание:\n{_esc_tg(res.get('description', ''))}\n\n"
                   f"Фото приложу при публикации на OLX (после подтверждения телефона).")
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Генератор объявлений OLX ----
    if any(w in t for w in ("создай объявление", "создай объявлени", "новое объявление на олх",
                            "создай объявления", "создай объявления из списка",
                            "напиши объявление")):
        import subprocess as _sp
        if "из списка" in t or "массов" in t:
            body = re.sub(r"^(создай объявления из списка|создай массово)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            if not body:
                api.send_message(chat_id, "📋 «создай объявления из списка: деталь1; деталь2; деталь3»")
                return True
            api.send_message(chat_id, "⏳ Генерирую объявления (по одному, быстро)…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"),
                         "gen_many", body], capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error", "error": (r.stderr or "?")[-150:]}
            if res.get("status") == "ok":
                ads = res.get("ads") or []
                lines = ["📋 <b>Сгенерированные объявления:</b>"]
                for i, a in enumerate(ads, 1):
                    lines.append(f"{i}. <b>{_esc_tg(a.get('title', ''))}</b> — {a.get('price', '?')} грн")
                lines.append("\nСоздать на OLX: «создай объявление: <деталь>» (нужно подтвердить телефон)")
                api.send_message(chat_id, "\n".join(lines)[:3900])
            else:
                api.send_message(chat_id, f"❌ {res.get('error', '?')}")
            return True
        # одно объявление
        part = re.sub(r"^(создай объявление|создай новое объявление|напиши объявление)\s*(на олх)?\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        part = part.replace("олх", "").replace("olx", "").strip(" ,.;:—–")
        if not part:
            api.send_message(chat_id, "📝 «создай объявление: фара BMW X5 2000 грн»")
            return True
        api.send_message(chat_id, "⏳ Генерирую объявление через AI…")
        _last_gen_ad[chat_id] = part
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "gen", part],
                    capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-150:]}
        if res.get("status") == "ok":
            txt = (f"📝 <b>Сгенерировано объявление:</b>\n"
                   f"Заголовок: <b>{_esc_tg(res.get('title', ''))}</b>\n"
                   f"Цена: {res.get('price', '?')} грн\n\n"
                   f"Описание:\n{_esc_tg(res.get('description', ''))}\n\n"
                   f"Публиковать на OLX? Напишите «опубликуй это объявление» — "
                   f"но сначала нужно подтвердить телефон в профиле (через VNC).")
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Мониторинг цен OLX ----
    if any(w in t for w in ("следи за ценой", "мониторинг цен", "цена на олх", "снизил",
                            "отпишись от цены", "цены на олх", "мои цены")):
        subs_file = PROJECT_ROOT / "data" / "olx_price_subs.json"
        try:
            subs = json.loads(subs_file.read_text(encoding="utf-8"))
        except Exception:
            subs = {}
        if "отпишись от цены" in t or "убери цену" in t:
            q = re.sub(r"(отпишись от цены|убери цену)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            cur = subs.get(str(chat_id), [])
            cur = [e for e in cur if e.get("query", "").lower() != q.lower()]
            subs[str(chat_id)] = cur
            subs_file.parent.mkdir(parents=True, exist_ok=True)
            subs_file.write_text(json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8")
            api.send_message(chat_id, f"📉 Отписался от цены «{q}».")
            return True
        if "мои цены" in t or ("цены" in t and not any(w in t for w in ("следи", "монитор"))):
            cur = subs.get(str(chat_id), [])
            if not cur:
                api.send_message(chat_id, "📉 Нет подписок на цены. «следи за ценой &lt;запрос&gt;»")
            else:
                api.send_message(chat_id, "📉 <b>Подписки на цены:</b>\n" + "\n".join(
                    f"• {_esc_tg(e.get('query'))} — мин {e.get('last_min') or '?'} грн" for e in cur))
            return True
        # добавить подписку
        q = re.sub(r"(следи за ценой|мониторинг цены|цена на олх)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        if not q:
            api.send_message(chat_id, "📉 «следи за ценой &lt;запрос&gt;», например: следи за ценой фары BMW X5")
            return True
        cur = subs.get(str(chat_id), [])
        if any(e.get("query", "").lower() == q.lower() for e in cur):
            api.send_message(chat_id, f"📉 Уже слежу за «{q}».")
            return True
        # проверить текущую минимальную цену
        import subprocess as _sp
        try:
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_price_alerts.py"),
                         "--probe", q], capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        except Exception:
            r = None
        cur_min = None
        if r and r.stdout:
            try:
                cur_min = float(r.stdout.strip())
            except Exception:
                pass
        cur.append({"query": q, "last_min": cur_min,
                    "since": datetime.now().strftime("%Y-%m-%d %H:%M")})
        subs[str(chat_id)] = cur
        subs_file.parent.mkdir(parents=True, exist_ok=True)
        subs_file.write_text(json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8")
        api.send_message(chat_id,
                         f"📉 Слежу за ценой «{q}»" +
                         (f". Сейчас минимум: {cur_min} грн" if cur_min else "") +
                         ".\nУведомлю при снижении >5%. «мои цены» — список, «отпишись от цены &lt;запрос&gt;» — убрать.")
        return True

    # ---- Единый инбокс ----
    if any(w in t for w in ("инбокс", "inbox", "все сообщения", "всё в одном",
                            "сводка сообщений", "где что новое", "проверь всё")):
        filters = _parse_inbox_filters(text)
        api.send_message(chat_id, "⏳ Собираю инбокс (почта, TG, IG, Messenger, Viber, Signal, OLX)… ~1 мин")
        items, summary = _collect_inbox(filters)
        if not items:
            api.send_message(chat_id, "📭 Везде пусто (или не удалось собрать).")
            return True
        _last_inbox[chat_id] = items
        txt = _format_inbox(items, filters)
        # умное резюме (если запрошено «сводка» или всегда кратко)
        if "сводк" in t or "резюме" in t or "кратко" in t or "умн" in t:
            api.send_message(chat_id, "🧠 Составляю умное резюме…")
            api.send_message(chat_id, _inbox_summarize(items)[:3900])
        else:
            api.send_message(chat_id, txt, reply_markup=_inbox_keyboard(items))
            api.send_message(chat_id,
                             "ℹ️ «сводка» — умное резюме · «ответь на N: …» — ответить\n"
                             "«озвучь инбокс» — голосом · «инбокс только непрочитанное» — фильтр")
        return True

    # ---- Ответы из инбокса ----
    m_reply = re.match(r"^(ответь|reply|отв[её]ть)\s+(?:на\s+)?#?(\d+)\s*:?\s*(.+)$", text, re.IGNORECASE)
    if m_reply and chat_id in _last_inbox:
        idx = int(m_reply.group(2))
        body = m_reply.group(3).strip()
        if 1 <= idx <= len(_last_inbox[chat_id]):
            _inbox_reply(api, chat_id, _last_inbox[chat_id][idx - 1], body)
            return True
        api.send_message(chat_id, f"❌ Нет пункта №{idx} в последнем инбоксе.")
        return True

    # ---- Озвучить инбокс ----
    if any(w in t for w in ("озвучь инбокс", "озвучь всё", "голосом инбокс", "прочитай инбокс вслух")):
        api.send_message(chat_id, "⏳ Собираю и озвучиваю…")
        items, summary = _collect_inbox({})
        if not items:
            api.send_message(chat_id, "📭 Везде пусто.")
            return True
        _last_inbox[chat_id] = items
        _inbox_voice(api, chat_id, items)
        return True

    # ---- Поиск по всем каналам ----
    m_glob = re.match(r"^(найди во всех|ищи везде|найди везде|поиск по всем)\s*(?:чатах|сообщениях|каналах)?\s*:?\s*(.+)$", text, re.IGNORECASE)
    if m_glob:
        q = m_glob.group(2).strip()
        if not q:
            api.send_message(chat_id, "🔍 «найди во всех чатах &lt;запрос&gt;»")
            return True
        api.send_message(chat_id, f"🔍 Ищу «{q}» по почте, TG, IG, Messenger… (может занять 1-2 мин)")
        _inbox_search(api, chat_id, q)
        return True

    # ---- Отметить всё прочитанным ----
    if any(w in t for w in ("отметь всё прочитанным", "отметить все прочитанными", "всё прочитано",
                            "отметь прочитанным")):
        _inbox_mark_read(api, chat_id)
        return True

    # ---- SMS-уведомления (вкл/выкл) ----
    if any(w in t for w in ("включи смс-уведомления", "включи уведомления о смс", "смс-алерты вкл",
                            "включи смс уведомления", "смс уведомления вкл")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_sms_alerts.py"), "--on"],
                    capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        api.send_message(chat_id, "🔔 SMS-уведомления <b>включены</b>: новые важные SMS (коды, OLX, Новая Почта, банки) будут приходить сюда.")
        return True
    if any(w in t for w in ("выключи смс-уведомления", "отключи уведомления о смс", "смс-алерты выкл",
                            "выключи смс уведомления", "смс уведомления выкл")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_sms_alerts.py"), "--off"],
                    capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        api.send_message(chat_id, "🔕 SMS-уведомления <b>выключены</b>. «мои смс» — по-прежнему можно читать вручную.")
        return True
    if any(w in t for w in ("статус смс-уведомлений", "смс-уведомления статус", "работают ли смс-уведомления")):
        try:
            st = json.loads((PROJECT_ROOT / "data" / "sms_alerts_state.json").read_text(encoding="utf-8"))
            api.send_message(chat_id,
                             f"🔔 SMS-уведомления: {'<b>включены</b>' if st.get('enabled', True) else '<b>выключены</b>'}\n"
                             f"Отправлено уведомлений: {st.get('notified', 0)}\n"
                             f"Проверка: {st.get('last_check', '—')[:16]}")
        except Exception:
            api.send_message(chat_id, "🔔 SMS-уведомления ещё не инициализированы (запустится автоматически).")
        return True

    # ---- SMS (Google Messages for Web, телефон +380959052288) ----
    if any(w in t for w in ("мои смс", "последние смс", "последняя смс", "проверь смс",
                            "смс на телефон", "что пришло по смс", "мои смски")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Читаю SMS с телефона…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "messages", "latest", "--limit", "10"],
                    capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            sms = res.get("sms") or []
            if not sms:
                api.send_message(chat_id, "📭 В SMS пусто.")
            else:
                lines = ["💬 <b>Последние SMS:</b>"]
                for s in sms[:10]:
                    code = f" · 🔑 <b>{s.get('code')}</b>" if s.get("code") else ""
                    lines.append(f"• <b>{_esc_tg(s.get('sender'))}</b>{code}: {_esc_tg(s.get('text', ''))[:90]}")
                api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось прочитать SMS')}")
        return True

    m_code = re.match(r"^(?:найди код из смс|код из смс|код подтверждения|какой код|код от)\s*(?:от|с)?\s*:?\s*(.*)$",
                      text, re.IGNORECASE)
    if m_code and ("код" in text.lower() or "смс" in text.lower()):
        sender = m_code.group(1).strip()
        import subprocess as _sp
        api.send_message(chat_id, f"🔑 Ищу код в SMS{f' от «{sender}»' if sender else ''}…")
        args = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                "messages", "code"]
        if sender:
            args.append(sender)
        r = _sp.run(args, capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            api.send_message(chat_id,
                             f"🔑 <b>Код: {res.get('code')}</b>\n"
                             f"От: {_esc_tg(res.get('sender'))}\n{_esc_tg(res.get('message'))[:150]}")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Код не найден')}")
        return True

    m_msgs_read = re.match(r"^(?:прочитай смс от|переписка|смс от|покажи переписку)\s+([^\n]{1,60})$",
                           text, re.IGNORECASE)
    if m_msgs_read:
        contact = m_msgs_read.group(1).strip().strip("«»\"'")
        import subprocess as _sp
        api.send_message(chat_id, f"💬 Открываю переписку с «{contact}»…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "messages", "read", contact, "--limit", "12"],
                    capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            msgs = res.get("messages") or []
            lines = [f"💬 <b>{_esc_tg(contact)}</b>:"]
            for m in msgs[:12]:
                lines.append(f"• {_esc_tg(m.get('text', ''))[:160]}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось прочитать переписку')}")
        return True

    m_msgs_send = re.match(r"^(?:отправь смс|напиши смс|отправь sms)\s+([^\n:]+)\s*:\s*(.+)$",
                           text, re.IGNORECASE)
    if m_msgs_send:
        contact = m_msgs_send.group(1).strip().strip("«»\"'")
        body = m_msgs_send.group(2).strip()
        _pending_confirm[chat_id] = {"kind": "messages_send",
                                     "data": {"to": contact, "text": body}}
        api.send_message(chat_id,
                         f"📨 Отправить SMS на «{_esc_tg(contact)}»:\n{_esc_tg(body)[:200]}\n\n«да» / «нет»")
        return True

    if any(w in t for w in ("покажи смс", "скрин смс", "скриншот смс")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Делаю скриншот Messages…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "messages", "screenshot"], capture_output=True, text=True,
                    timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok" and res.get("screenshot"):
            _acct_send_result(api, chat_id, {"status": "ok", "text": "💬 Экран Messages",
                                             "screenshot": res["screenshot"],
                                             "caption": "💬 Messages"}, "")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось сделать скриншот')}")
        return True

    # ---- Массовая выгрузка склада на OLX ----
    if any(w in t for w in ("выложи весь склад", "выгрузи склад на олх", "опубликуй весь склад",
                            "склад на олх", "выложи склад", "выгрузи склад",
                            "все объявления со склада", "весь склад на олх", "склад на olx")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Читаю склад и генерирую объявления…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "export_sklad"],
                    capture_output=True, text=True, timeout=180, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") != "ok":
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось прочитать склад')}")
            return True
        results = res.get("results") or []
        if not results:
            api.send_message(chat_id, "📦 Склад пуст — добавьте детали: «добавь деталь: …»")
            return True
        lines = ["📦 <b>Склад → OLX:</b>"]
        for x in results[:20]:
            st = "✅" if x.get("status") == "ok" else "❌"
            lines.append(f"{st} {_esc_tg(x.get('name'))} — {x.get('price_gen') or x.get('price')} грн")
        lines.append("\n" + (f"Всего: {res.get('total')} позиций. Опубликовать на OLX?" if res.get('err') == 0
                             else f"Готово {res.get('ok')} из {res.get('total')}. Опубликовать готовые?"))
        _pending_confirm[chat_id] = {"kind": "olx_bulk", "data": {"total": res.get("total")}}
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    # ---- Клиенты и отправки Новой Почты ----
    m_client = re.match(r"^(?:добавь клиента|запиши клиента)\s*:\s*(.+)$", text, re.IGNORECASE)
    if m_client:
        parts = [p.strip() for p in re.split(r"[,;]|, ", m_client.group(1)) if p.strip()]
        if len(parts) < 2:
            api.send_message(chat_id, "📇 Формат: «добавь клиента: ФИО, телефон, город, отделение»")
            return True
        name = parts[0]
        phone = parts[1]
        city = parts[2] if len(parts) > 2 else ""
        wh = parts[3] if len(parts) > 3 else ""
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"),
                     "add_client", name, phone, city, wh], capture_output=True, text=True,
                    timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            c = res.get("client", {})
            api.send_message(chat_id, f"📇 <b>{c.get('name')}</b> — {c.get('phone')} · {c.get('city')} {c.get('warehouse')} · {res.get('msg')}")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    if any(w in t for w in ("мои клиенты", "список клиентов", "клиенты")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"), "clients"],
                    capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok" and res.get("clients"):
            lines = ["📇 <b>Клиенты:</b>"]
            for c in res["clients"][:15]:
                lines.append(f"• <b>{_esc_tg(c.get('name'))}</b> — {c.get('phone')} · {c.get('city')} {c.get('warehouse')}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, "📇 Клиентов пока нет. «добавь клиента: ФИО, телефон, город, отделение»")
        return True

    m_ship = re.match(r"^(?:запиши отправку|отправить|отправка)\s*:\s*(.+)$", text, re.IGNORECASE)
    if m_ship:
        # «деталь» -> «получатель» (клиент по имени) или «деталь»: ФИО, телефон, город, отделение
        spec = m_ship.group(1).strip()
        parts = [p.strip() for p in spec.split(",") if p.strip()]
        detail = parts[0]
        if len(parts) >= 3 and "@" in "".join(parts[1:2]):
            pass
        import subprocess as _sp
        if len(parts) >= 3:
            # деталь, ФИО, телефон[, город, отделение]
            cmd = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"),
                   "ship", detail, parts[1], parts[2],
                   parts[3] if len(parts) > 3 else "",
                   parts[4] if len(parts) > 4 else ""]
        else:
            # деталь -> клиент (имя из базы)
            client_ref = parts[1] if len(parts) > 1 else ""
            cmd = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"),
                   "ship", detail, client_ref]
        r = _sp.run(cmd, capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            s = res.get("shipment", {})
            api.send_message(chat_id,
                             f"📦 <b>Отправка:</b> {_esc_tg(s.get('detail'))} → {_esc_tg(s.get('recipient'))}\n"
                             f"📞 {s.get('phone')} · {s.get('city')} {s.get('warehouse')}\n"
                             f"Статус: {s.get('status')}")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}\nСначала «добавь клиента: ФИО, телефон, город, отделение»")
        return True

    if any(w in t for w in ("мои отправки", "отправки", "заказы на отправку")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"), "ships"],
                    capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok" and res.get("shipments"):
            lines = ["📦 <b>Отправки:</b>"]
            for s in res["shipments"][:12]:
                lines.append(f"• {_esc_tg(s.get('detail'))} → {_esc_tg(s.get('recipient'))} ({s.get('status')})")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, "📦 Отправок пока нет.")
        return True

    # ---- Отчёт по OLX ----
    if any(w in t for w in ("отчёт по олх", "отчет по олх", "отчёт олх", "сводка олх",
                            "статистика олх", "сколько объявлений на олх", "сводка по олх")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Собираю отчёт по OLX…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_report.py")],
                    capture_output=True, text=True, timeout=150, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        from run_olx_report import format_report
        api.send_message(chat_id, format_report(res)[:3900])
        return True

    # ---- Новая Почта: создание ТТН ----
    m_ttn = re.match(r"^(?:создай ттн|создать ттн|накладная|создай накладную)\s*:?\s*(.+)$",
                     text, re.IGNORECASE)
    if m_ttn:
        # формат: деталь, цена, ФИО, телефон, город, отделение
        parts = [p.strip() for p in re.split(r"[,;]", m_ttn.group(1)) if p.strip()]
        if len(parts) < 6:
            api.send_message(chat_id,
                             "📦 Формат: «создай ттн: деталь, цена, ФИО, телефон, город, отделение»\n"
                             "Пример: создай ттн: фара BMW X5, 2000, Іван Петренко, 0671234567, Київ, Відділення №1")
            return True
        detail, cost, recipient, phone, city, wh = parts[:6]
        _pending_confirm[chat_id] = {"kind": "ttn_create",
                                     "data": {"detail": detail, "cost": cost,
                                              "recipient": recipient, "phone": phone,
                                              "city": city, "warehouse": wh}}
        api.send_message(chat_id,
                         f"📦 Создать ТТН Новой Почты:\n"
                         f"Деталь: <b>{_esc_tg(detail)}</b> · {cost} грн\n"
                         f"Получатель: {_esc_tg(recipient)} · {phone}\n"
                         f"{_esc_tg(city)} · {_esc_tg(wh)}\n\n«да» / «нет»")
        return True

    if any(w in t for w in ("проверь ттн", "настройки ттн", "готов ли отправитель нп",
                            "отправитель новой почты")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_ttn.py"), "whoami"],
                    capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            s = res.get("sender", {})
            if s.get("ready"):
                api.send_message(chat_id,
                                 f"✅ Отправитель НП готов: <b>{_esc_tg(s.get('description'))}</b>\n"
                                 f"Адрес: {_esc_tg(s.get('address') or '—')}\n"
                                 f"Можно создавать ТТН: «создай ттн: …»")
            else:
                api.send_message(chat_id,
                                 "⚠️ <b>Отправитель НП не настроен</b> в кабинете API.\n"
                                 "1. Зайдите: cabinet.novaposhta.ua\n"
                                 "2. Настройки → «Мои данные/Отправитель»\n"
                                 "3. Заполните ФИО, телефон +380959052288 и адрес отправки "
                                 "(напр. Відділення №8, Кропивницький)\n"
                                 "После этого напишите «проверь ттн» — и создание накладных заработает.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- OLX-чат (сообщения покупателей) ----
    if any(w in t for w in ("сообщения на олх", "переписки олх", "чат олх", "сообщения в олх",
                            "переписки на олх", "чат на олх", "что пишут на олх")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Открываю чат OLX…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "olx", "chat", "list"], capture_output=True, text=True, timeout=120,
                    cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") != "ok":
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось открыть чат')}")
            return True
        threads = res.get("threads") or []
        if not threads:
            api.send_message(chat_id, "💬 В чате OLX пока нет переписок.")
            return True
        lines = ["💬 <b>OLX-чат:</b>"]
        for x in threads[:12]:
            lines.append(f"• <b>{_esc_tg(x.get('name'))}</b>: {_esc_tg(x.get('text', ''))[:80]}")
        if res.get("unread_present"):
            lines.append("\n🔴 Есть непрочитанные!")
        lines.append("\nЧитать: «прочитай чат <имя>» · Ответить: «ответь покупателю на олх: <имя>: <текст>»")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    m_chat_read = re.match(r"^(?:прочитай чат|сообщения от|переписка с|чат с)\s+([^\n]{1,50})$",
                           text, re.IGNORECASE)
    # не перехватываем чужие мессенджеры (телега, вайбер, тикток и т.п.)
    if m_chat_read and not any(x in text.lower() for x in (
            "телеграм", "телеге", "теге", "тегу", "тегу", "тг", "тикток", "tiktok",
            "вайбер", "viber", "signal", "сигнал", "вотсап", "whatsapp", "мессенджер", "messenger")):
        contact = m_chat_read.group(1).strip().strip("«»\"'")
        import subprocess as _sp
        api.send_message(chat_id, f"💬 Читаю переписку с «{contact}»…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "olx", "chat", "read", contact], capture_output=True, text=True, timeout=120,
                    cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") != "ok":
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось прочитать')}")
            return True
        msgs = res.get("messages") or []
        if not msgs:
            api.send_message(chat_id, f"💬 С «{contact}» сообщений нет.")
            return True
        lines = [f"💬 <b>{_esc_tg(contact)}</b>:"]
        for m in msgs[:15]:
            who = "👤" if not m.get("mine") else "🙋"
            lines.append(f"{who} {_esc_tg(m.get('text', ''))[:200]}")
        lines.append("\nОтветить: «ответь покупателю на олх: <имя>: <текст>»")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    m_chat_reply = re.match(r"^(?:ответь покупателю на олх|ответь на олх|ответь в олх)\s*[:\-]?\s*([^:\n]{1,50})\s*:\s*(.+)$",
                            text, re.IGNORECASE)
    if m_chat_reply:
        contact = m_chat_reply.group(1).strip().strip("«»\"'")
        body = m_chat_reply.group(2).strip()
        _pending_confirm[chat_id] = {"kind": "olx_chat_reply",
                                     "data": {"to": contact, "text": body}}
        api.send_message(chat_id,
                         f"📨 Ответ покупателю «{_esc_tg(contact)}»:\n{_esc_tg(body)[:300]}\n\n«да» / «нет»")
        return True

    # ---- Поднятие/контроль объявлений OLX ----
    if any(w in t for w in ("подними объявления", "подними мои объявления", "обнови объявления",
                            "мои объявления олх", "мои объявления olx", "контроль объявлений",
                            "сколько объявлений")):
        import subprocess as _sp
        do_boost = "подними" in t or "обнови" in t or "поднять" in t
        api.send_message(chat_id, "⏳ Открываю кабинет OLX…")
        args = ["--boost"] if do_boost else []
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_boost.py")] + args,
                    capture_output=True, text=True, timeout=170, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            txt = (f"🛒 <b>Объявления OLX</b>\n"
                   f"Найдено объявлений: {res.get('ads_found') or 0}\n"
                   f"Кнопок «поднять»: {res.get('refresh_buttons') or 0}")
            if res.get("boosted"):
                txt += "\n✅ Первое объявление поднято!"
            if res.get("ads_preview"):
                txt += "\n\n" + "\n".join(f"• {_esc_tg(x)}" for x in res["ads_preview"][:5])
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": res.get("screenshot"),
                                             "caption": "🛒 Объявления OLX"}, "")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Удаление/редактирование объявлений OLX ----
    m_del = re.match(r"^(удали объявление|удалить объявление|удали|сними объявление|снять объявление)\s*(?:№\s*)?(\d{5,12})\b", text, re.IGNORECASE)
    if m_del:
        ad_id = m_del.group(2)
        _pending_confirm[chat_id] = {"kind": "olx_delete", "data": {"ad_id": ad_id}}
        api.send_message(chat_id, f"🗑 Удалить объявление <b>{ad_id}</b> с OLX?\n«да» / «нет»")
        return True

    m_edit = re.match(r"^(отредактируй объявление|редактируй объявление|измени объявление|обнови объявление)\s*(?:№\s*)?(\d{5,12})\b\s*:?\s*(.*)$", text, re.IGNORECASE)
    if m_edit:
        ad_id = m_edit.group(2)
        edit_spec = m_edit.group(3).strip()
        # парсим: «цена 1500», «заголовок …», «описание …»
        title = description = price = ""
        m_p = re.search(r"(?:цена|ціна)\s+(\d{2,7})", edit_spec, re.IGNORECASE)
        if m_p:
            price = m_p.group(1)
        m_t = re.search(r"(?:заголовок|название|назва)\s*[:—-]\s*(.+)", edit_spec, re.IGNORECASE)
        if m_t:
            title = m_t.group(1).strip().split(",")[0][:150]
        m_d = re.search(r"(?:описание|опис)\s*[:—-]\s*(.+)", edit_spec, re.IGNORECASE)
        if m_d:
            description = m_d.group(1).strip()
        if not (title or description or price):
            api.send_message(chat_id, "📝 Формат: «отредактируй объявление &lt;id&gt;: цена 1500, заголовок: …»\n"
                                      "или «отредактируй объявление &lt;id&gt;: описание: …»")
            return True
        _pending_confirm[chat_id] = {"kind": "olx_edit",
                                     "data": {"ad_id": ad_id, "title": title,
                                              "description": description, "price": price}}
        api.send_message(chat_id, f"📝 Отредактировать объявление <b>{ad_id}</b>:\n"
                                  f"{'Цена: ' + price + chr(10) if price else ''}"
                                  f"{'Заголовок: ' + title + chr(10) if title else ''}"
                                  f"{'Описание: ' + description[:80] if description else ''}"
                                  f"\n\n«да» / «нет»")
        return True

    if any(w in t for w in ("мои объявления", "мои объявлени", "список объявлений",
                            "какие у меня объявления")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Загружаю мои объявления…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "olx", "my_ads"], capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            if res.get("ads"):
                lines = ["🛒 <b>Мои объявления OLX:</b>"]
                for a in res["ads"][:15]:
                    lines.append(f"• <b>{_esc_tg(a.get('title', '?'))}</b> — {a.get('price', '?')} грн · id {a.get('id')}")
                lines.append("\nУдалить: «удали объявление &lt;id&gt;» · Редактировать: «отредактируй объявление &lt;id&gt;: цена 1500»")
                api.send_message(chat_id, "\n".join(lines)[:3900])
            else:
                api.send_message(chat_id, "🛒 Сейчас опубликованных объявлений нет.\n"
                                          "Создать: «создай объявление: <деталь>» → «опубликуй это объявление»\n"
                                          "id появится в журнале после публикации.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось получить список объявлений')}")
        return True

    # ---- Подтверждение телефона OLX + публикация ----
    if any(w in t for w in ("подтверди телефон олх", "подтверди телефон olx", "подтвердить телефон олх",
                            "подтверждение телефона олх")):
        api.send_message(chat_id,
                         "📱 <b>Подтверждение телефона OLX</b>\n\n"
                         "Это одноразовое действие (как вход в соцсети):\n"
                         "1. Я открою VNC и страницу подтверждения\n"
                         "2. Подключитесь: <code>167.233.95.7:5901</code> (пароль <code>aios1234</code>)\n"
                         "3. Введите номер телефона, нажмите «Отримати код», введите код из Viber/SMS\n"
                         "4. Готово — напишите мне, я закрою VNC, и публикация объявлений заработает.\n\n"
                         "Открываю VNC сейчас…")
        import subprocess as _sp
        try:
            _sp.run(["ufw", "allow", "5901/tcp"], capture_output=True, timeout=15)
            _sp.run(["bash", "-c", "pkill -9 -f '[X]vnc :1' 2>/dev/null; sleep 1; "
                                    "vncserver :1 -geometry 1920x1080 -depth 24 -localhost no >/dev/null 2>&1"],
                    capture_output=True, timeout=60)
            _sp.run(["bash", "-c",
                     "export DISPLAY=:1; rm -f /root/AIOS/data/chrome_twin/default/Singleton*; "
                     "nohup /usr/bin/google-chrome-stable --no-sandbox "
                     "--user-data-dir=/root/AIOS/data/chrome_twin/default "
                     "--no-first-run --no-default-browser-check --disable-infobars "
                     "\"https://www.olx.ua/d/uk/adding/\" > /tmp/olx_confirm.log 2>&1 &"],
                    capture_output=True, timeout=30)
            api.send_message(chat_id, "✅ VNC открыт. Жду вас: <code>167.233.95.7:5901</code>, пароль <code>aios1234</code>")
        except Exception as e:
            api.send_message(chat_id, f"⚠️ Не смог открыть VNC: {e}")
        return True

    if any(w in t for w in ("опубликуй это объявление", "опубликуй объявление на олх",
                            "публикуй на олх", "создай на олх", "выложи на олх",
                            "опубликуй объявление", "опубликовать объявление",
                            "выложи объявление", "публикуй объявление", "опубликуй на олх",
                            "публикуй это объявление", "выложи это объявление")):
        # берём деталь из текста или из последнего сгенерированного
        m_d = re.search(r"(?:объявление|на олх|на олх:)\s*[:—-]\s*(.+)$", text, re.IGNORECASE)
        part = m_d.group(1).strip() if m_d else ""
        # «опубликуй это объявление» без детали — берём из памяти
        if not part and "это объявление" in t:
            part = _last_gen_ad.get(chat_id, "")
        # убираем лишние слова из part
        part = re.sub(r"^(опубликуй|опубликовать|выложи|публикуй)\s*(это\s+)?объявление\s*(на олх)?\s*:?\s*",
                      "", part, flags=re.IGNORECASE).strip()
        part = part.replace("олх", "").replace("olx", "").strip(" ,.;:—–")
        if not part:
            api.send_message(chat_id, "📝 Скажите, что публикуем: «опубликуй на олх: фара BMW X5 2000»\n"
                                      "или сначала «создай объявление: …», потом «опубликуй это объявление»")
            return True
        import subprocess as _sp
        api.send_message(chat_id, f"⏳ Создаю объявление на OLX: «{part}»…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "create", part],
                    capture_output=True, text=True, timeout=170, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "need_confirm":
            _pending_confirm[chat_id] = {"kind": "olx_create",
                                         "data": {"part": part,
                                                  "title": res.get("title", ""),
                                                  "description": res.get("description", ""),
                                                  "price": res.get("price", "")}}
            api.send_message(chat_id,
                             f"📝 Объявление готово:\n<b>{res.get('title')}</b>\n"
                             f"Цена: {res.get('price')} грн\n"
                             f"{res.get('description', '')}\n\n"
                             f"Опубликовать на OLX? «да» / «нет»")
        elif res.get("status") == "phone_not_confirmed":
            api.send_message(chat_id,
                             f"📱 {res.get('error')}\n\n"
                             f"Напишите «подтверди телефон OLX» — открою VNC для одноразового подтверждения.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', res.get('status', '?'))}")
        return True

    # ---- Автоответ OLX ----
    if any(w in t for w in ("автоответ олх", "автоответ olx", "автоответ в олх",
                            "автоответ покупателям")):
        cfg_file = PROJECT_ROOT / "data" / "olx_autoreply.json"
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
        if "выключ" in t or "отключ" in t:
            cfg["enabled"] = False
            cfg_file.parent.mkdir(parents=True, exist_ok=True)
            cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            api.send_message(chat_id, "🔕 Автоответ OLX выключен.")
            return True
        auto = "на автомате" in t
        cfg["enabled"] = True
        cfg["auto_send"] = auto
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        api.send_message(chat_id,
                         f"🔔 Автоответ OLX включён{' (на автомате)' if auto else ''}.\n"
                         f"При новых сообщениях в OLX-чате бот уведомит и поможет ответить.\n"
                         f"{'Отправка ответов — автоматически.' if auto else 'Сначала — подтверждение в чате.'}")
        return True

    # ---- Сколько стоит деталь (умные цены) ----
    if re.match(r"^(сколько стоит|почём|цена на|что стоит)\s+", t):
        q = re.sub(r"^(сколько стоит|почём|цена на|что стоит)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        q = q.replace("?", "").strip()
        if not q:
            api.send_message(chat_id, "💰 «сколько стоит <деталь>», например: сколько стоит фара BMW X5")
            return True
        api.send_message(chat_id, f"💰 Ищу цену на «{q}»…")
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_price_guide.py"), q],
                    capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-150:]}
        if res.get("status") == "ok":
            if res.get("found"):
                txt = (f"💰 <b>Цена на «{q}»</b> (по {res['found']} похожим объявлениям):\n"
                       f"📊 Медиана: <b>{res.get('median')} грн</b>\n"
                       f"📉 Диапазон: {res.get('min')} – {res.get('max')} грн")
                if res.get("ai_advice"):
                    txt += f"\n\n🤖 <i>{_esc_tg(res['ai_advice'])}</i>"
                if res.get("examples"):
                    txt += "\n\nПримеры:\n" + "\n".join(
                        f"• {_esc_tg(e['title'][:55])} — {e['price']} грн" for e in res["examples"][:3])
                api.send_message(chat_id, txt[:3900])
            else:
                api.send_message(chat_id,
                                 f"💰 По «{q}» пока нет данных в базе.\n"
                                 f"Могу: «следи за ценой {q}» — буду собирать и уведомлять о снижении.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Кто продаёт дешевле (топ выгодных) ----
    if re.match(r"^(кто продаёт дешевле|кто продает дешевле|где дешевле|топ выгодных|лучшая цена)", t):
        q = re.sub(r"^(кто продаёт дешевле|кто продает дешевле|где дешевле|топ выгодных|лучшая цена)\s*:?\s*",
                   "", text, flags=re.IGNORECASE).strip()
        q = q.replace("?", "").strip()
        if not q:
            api.send_message(chat_id, "💰 «кто продаёт дешевле <деталь>», например: кто продаёт дешевле стартер ВАЗ")
            return True
        api.send_message(chat_id, f"💰 Ищу лучшие цены на «{q}»…")
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_price_guide.py"), "cheap", q],
                    capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-150:]}
        if res.get("status") == "ok" and res.get("cheapest"):
            lines = [f"💰 <b>Лучшие цены на «{q}»</b> (медиана {res.get('median')} грн):"]
            for i, s in enumerate(res["cheapest"], 1):
                lines.append(f"{i}. <b>{s['price']} грн</b> — {_esc_tg(s['title'][:55])}\n"
                             f"   {_esc_tg(s.get('city') or '')} · <a href=\"{s.get('url', '#')}\">открыть</a>")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        elif res.get("note"):
            api.send_message(chat_id, f"💰 «{q}» пока нет в базе. «следи за ценой {q}» — начну собирать.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- AI-классификатор при добавлении детали ----
    if re.match(r"^добавь деталь\s+.+,\s*\d+\s*шт", t):
        import subprocess as _sp
        m_add = re.match(r"^добавь деталь\s+(.+?)\s*[,:]\s*(\d+)\s*шт\s*(?:по\s*([\d\s.,]+))?", text, re.IGNORECASE)
        if m_add:
            name = m_add.group(1).strip()
            qty = int(m_add.group(2))
            price_s = m_add.group(3) or ""
            # LLM-классификация: категория + рекомендуемая цена
            prompt = (f"Деталь автозапчасти: «{name}». Определи категорию из списка "
                      f"(двигатель, кузов, оптика, подвеска, тормоза, электрика, салон, трансмиссия, расходники, другое) "
                      f"и среднюю цену в грн. Верни ТОЛЬКО JSON: {{\"category\": \"...\", \"price\": число}}. "
                      f"{('Ориентир по цене: ' + price_s + ' грн') if price_s else ''}")
            try:
                advice = _llm_chat_direct(prompt)
                import json as _json2
                start = advice.find("{")
                end = advice.rfind("}") + 1
                cls = _json2.loads(advice[start:end]) if start >= 0 and end > start else {}
                category = (cls.get("category") or "общее")
                rec_price = cls.get("price") or price_s or "0"
            except Exception:
                category, rec_price = "общее", price_s or "0"
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"),
                         "add", name, str(qty), str(rec_price or 0), category],
                        capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error"}
            if res.get("status") == "ok":
                it = res.get("item", {})
                api.send_message(chat_id,
                                 f"📦 <b>{name}</b>: {it.get('qty')} шт · {it.get('price')} грн\n"
                                 f"🏷 Категория (AI): {it.get('category')}\n"
                                 f"{'🤖 Рекомендуемая цена по рынку.' if rec_price and not price_s else ''}")
            else:
                api.send_message(chat_id, f"❌ {res.get('error', '?')}")
            return True

    # ---- Склад (инвентаризация) ----
    inv_words = any(w in t for w in ("добавь деталь", "добавь на склад", "спиши деталь",
                                     "что на складе", "склад", "найди деталь",
                                     "продал ", "продал: ", "продал деталь", "продана деталь",
                                     "остатки", "инвентаризац", "сколько деталей"))
    if inv_words:
        import subprocess as _sp
        # продажа: списать со склада + записать финансы
        m_sale = re.match(r"^(продал|продала|продана деталь)\s+(.+?)\s+за\s+([\d\s.,]+)", text, re.IGNORECASE) or \
                 re.match(r"^(продал|продала|продана деталь)\s+([\w\sА-Яа-яЁёІіЇїЄє'’.-]+?)\s+([\d\s.,]+)", text, re.IGNORECASE)
        if m_sale:
            name = m_sale.group(2).strip()
            try:
                price = float(m_sale.group(3).replace(" ", "").replace(",", "."))
            except ValueError:
                api.send_message(chat_id, "❌ Не понял цену. Формат: «продал фару 2000»")
                return True
            # списать со склада
            r1 = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"),
                          "take", name, "1"], capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                inv = json.loads((r1.stdout or "").strip().split("\n")[-1])
            except Exception:
                inv = {"status": "error"}
            # записать финансы
            r2 = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_finance.py"),
                          "add", "sale", str(price), name], capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                fin = json.loads((r2.stdout or "").strip().split("\n")[-1])
            except Exception:
                fin = {"status": "error"}
            txt = f"💰 <b>Продажа: {name}</b> — {price} грн\n"
            if inv.get("status") == "ok":
                it = inv.get("item", {})
                txt += f"📦 Склад: списано (осталось {it.get('qty')} шт)\n"
            elif inv.get("error"):
                txt += f"⚠️ {inv['error']}\n"
            if fin.get("status") == "ok":
                txt += "✅ Записано в финансы"
            # Снять связанное объявление безопасно: только если остаток этой
            # позиции исчерпан и журнал публикаций дал единственное совпадение.
            try:
                from aios_core.sales_lifecycle import SalesLifecycle
                olx_res = SalesLifecycle(PROJECT_ROOT).deactivate_olx_for_item(name, "manual_sale")
                if olx_res.get("status") == "deactivated":
                    txt += "\n🛒 OLX: объявление снято с публикации"
                elif olx_res.get("status") == "kept_active":
                    txt += f"\n🛒 OLX: объявление оставлено (ещё {olx_res.get('available_qty')} шт в остатке)"
                elif olx_res.get("status") in ("not_found", "ambiguous", "error"):
                    txt += "\n⚠️ OLX: не найдено однозначное объявление для снятия"
            except Exception:
                txt += "\n⚠️ OLX: не удалось проверить связанное объявление"
            api.send_message(chat_id, txt + "\n📦 Если нужна накладная НП: «создай ттн: деталь, цена, ФИО, телефон, город, отделение»")
            return True
        # добавление детали
        m_add = re.match(r"^(добавь деталь|добавь на склад)\s+(.+?)\s*[,:]\s*(\d+)\s*шт\s*(?:по\s*([\d\s.,]+))?", text, re.IGNORECASE)
        if m_add:
            name = m_add.group(1).strip()
            qty = int(m_add.group(2))
            price_s = m_add.group(3) or "0"
            try:
                price = float(price_s.replace(" ", "").replace(",", "."))
            except ValueError:
                price = 0
            _cmd_list = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"),
                         "add", name, str(qty), str(price)]
            _ph = _last_photo.get(chat_id, "")
            if _ph and os.path.exists(_ph):
                _cmd_list += ["--photo", _ph]
            r = _sp.run(_cmd_list, capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error", "error": (r.stderr or "?")[-100:]}
            if res.get("status") == "ok":
                it = res.get("item", {})
                photo_txt = " 📸+фото" if it.get("photo") else ""
                api.send_message(chat_id, f"📦 <b>{name}</b>: {it.get('qty')} шт ({it.get('price')} грн){photo_txt} — {res.get('msg', '')}")
            else:
                api.send_message(chat_id, f"❌ {res.get('error', '?')}")
            return True
        # «найди деталь» / поиск
        if "найди деталь" in t or "ищу деталь" in t or "есть ли" in t:
            q = re.sub(r"^(найди деталь|ищу деталь|есть ли)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            q = q.replace("на складе", "").strip()
            if not q:
                api.send_message(chat_id, "🔍 «найди деталь капот»")
                return True
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"), "search", q],
                        capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error"}
            if res.get("status") == "ok" and res.get("items"):
                lines = ["🔍 <b>Найдено на складе:</b>"]
                for it in res["items"][:8]:
                    available = it.get("available_qty", it.get("qty", 0))
                    reserved = it.get("reserved_qty", 0)
                    mark = "✅" if available > 0 else "❌"
                    reserve_note = f" · продано, ждёт отправки: {reserved}" if reserved else ""
                    lines.append(f"{mark} <b>{_esc_tg(it['name'])}</b> — свободно {available} из {it.get('qty')} шт · {it.get('price')} грн{reserve_note}")
                api.send_message(chat_id, "\n".join(lines))
            else:
                api.send_message(chat_id, f"🔍 «{q}» на складе нет.")
            return True
        # статистика/остатки
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"), "stats"],
                    capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error"}
        if res.get("status") == "ok":
            txt = (f"📦 <b>Склад</b>\n"
                   f"Деталей: {res.get('items_count')} · физически: {res.get('total_qty')} шт · "
                   f"свободно: {res.get('available_qty', res.get('total_qty'))} шт\n"
                   f"💰 Стоимость свободных запасов: {res.get('total_value')} грн")
            if res.get("reserved_qty"):
                txt += f"\n📌 Продано и ждёт отправки по созданным ТТН: {res.get('reserved_qty')} шт"
            if res.get("out_of_stock"):
                txt += "\n\n🚫 Закончились: " + ", ".join(_esc_tg(x) for x in res["out_of_stock"][:5])
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Финансовый учёт ----
    fin_words = any(w in t for w in ("запиши продажу", "запиши расход", "запиши трату",
                                     "продал за", "купил за", "потратил",
                                     "сколько заработал", "прибыль", "финанс", "учет",
                                     "учёт", "деньги за неделю", "деньги за месяц",
                                     "мои операции", "операции"))
    if fin_words:
        import subprocess as _sp
        # запись операции
        m_op = re.match(r"^(запиши продажу|запиши расход|запиши трату|продал за|купил за|потратил)\s+([\d\s.,]+)\s*(.*)$", text, re.IGNORECASE)
        if m_op:
            verb = m_op.group(1).lower()
            kind = "sale" if any(k in verb for k in ("продаж", "продал")) else "expense"
            try:
                amount = float(m_op.group(2).replace(" ", "").replace(",", "."))
            except ValueError:
                api.send_message(chat_id, "❌ Не понял сумму. Пример: «запиши продажу 2000 фара BMW»")
                return True
            desc = m_op.group(3).strip() or ("продажа" if kind == "sale" else "расход")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_finance.py"),
                         "add", kind, str(amount), desc],
                        capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error", "error": (r.stderr or "?")[-100:]}
            if res.get("status") == "ok":
                em = "💰" if kind == "sale" else "📉"
                api.send_message(chat_id, f"{em} Записал: {desc} — {amount} грн ({'продажа' if kind == 'sale' else 'расход'})")
            else:
                api.send_message(chat_id, f"❌ {res.get('error', '?')}")
            return True
        # отчёт
        days = 30
        m_days = re.search(r"за\s+(неделю|месяц|день)", t)
        if m_days:
            if "неделю" in m_days.group(1):
                days = 7
            elif "день" in m_days.group(1):
                days = 1
            else:
                days = 30
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_finance.py"), "report", str(days)],
                    capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            txt = (f"💰 <b>Финансы за {days} дн.</b>\n"
                   f"🟢 Продажи: {res.get('sales')} грн\n"
                   f"🔴 Расходы: {res.get('expenses')} грн\n"
                   f"📊 Прибыль: <b>{res.get('profit')}</b> грн\n"
                   f"({res.get('count')} операций)")
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Google Таблица из данных ----
    if any(w in t for w in ("создай гугл таблицу", "создай google таблицу", "в гугл таблицу",
                            "создай таблицу из финансов", "создай таблицу из склада")):
        import subprocess as _sp
        kind = "finance" if ("финанс" in t or "продаж" in t) else \
               ("inventory" if "склад" in t or "детал" in t else "finance")
        api.send_message(chat_id, f"⏳ Создаю Google Таблицу из {'финансов' if kind == 'finance' else 'склада'}…")
        # 1) CSV
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), kind],
                    capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-100:]}
        if res.get("status") != "ok" or not res.get("file"):
            api.send_message(chat_id, f"❌ Не удалось выгрузить данные: {res.get('error', '?')}")
            return True
        csv_path = res["file"]
        api.send_message(chat_id, "📄 Данные готовы. Открываю Google Sheets…")
        # 2) открыть sheets и вставить (через Chrome Twin)
        try:
            from aios_core.platforms.chrome_twin_adapter import ChromeTwinAdapter as _CTA
            a = _CTA()
            # используем исправленный запуск
            from playwright.async_api import async_playwright as _ap
            import asyncio as _ai

            async def _do():
                pw = await _ap().start()
                ctx = await pw.chromium.launch_persistent_context(
                    user_data_dir=str((PROJECT_ROOT / "data" / "chrome_twin" / "default").resolve()),
                    executable_path="/usr/bin/google-chrome-stable",
                    headless=False, slow_mo=80,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                          "--disable-dev-shm-usage"],
                    viewport={"width": 1440, "height": 900})
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await page.goto("https://docs.google.com/spreadsheets/create",
                                wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(9000)
                url = page.url
                # вставить CSV через первую ячейку (кликнуть A1 и вставить текст)
                try:
                    cell = page.locator("div#t-formula-bar-input, div[role='input']").first
                    # проще: кликнуть в A1 листа
                    a1 = page.locator("#t-0-0-0, [role='gridcell'][aria-colindex='1'][aria-rowindex='1']").first
                    if await a1.count():
                        await a1.click(force=True, timeout=5000)
                        await page.wait_for_timeout(800)
                        # вставить данные как текст в формулу-бар? Лучше: просто открыть и оставить
                except Exception:
                    pass
                await ctx.close()
                await pw.stop()
                return url
            url = _ai.run(_do())
            api.send_message(chat_id,
                             f"✅ <b>Google Таблица создана</b>:\n🔗 {url}\n\n"
                             f"CSV-файл с данными: {csv_path}\n"
                             f"(импортируйте его в таблицу: Файл → Импорт — или пришлите мне команду "
                             f"«экспортируй финансы в csv» для повторной выгрузки)")
        except Exception as e:
            api.send_message(chat_id, f"⚠️ Таблица создана, но не открыта: {e}\nCSV: {csv_path}")
        return True

    # ---- Вечерний отчёт ----
    if any(w in t for w in ("вечерний отчёт", "вечерний отчет", "итоги дня",
                            "отчёт за день", "отчет за день", "дневной отчёт")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Собираю отчёт…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_evening_report.py")],
                    capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        if "отправлен" in (r.stdout or ""):
            api.send_message(chat_id, "🌙 Вечерний отчёт отправлен ☺️")
        else:
            # показать локально
            import importlib.util as _iu2
            try:
                spec = _iu2.spec_from_file_location("evr", str(PROJECT_ROOT / "run_evening_report.py"))
                mod = _iu2.module_from_spec(spec)
                spec.loader.exec_module(mod)
                report = mod.build_report()
                api.send_message(chat_id, report[:3900])
            except Exception as e:
                api.send_message(chat_id, f"❌ {e}")
        return True

    # ---- Месячный отчёт ----
    if any(w in t for w in ("месячный отчёт", "месячный отчет", "отчёт за месяц",
                            "отчет за месяц", "отчёт за 30 дней", "сводка за месяц")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Собираю месячный отчёт…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_evening_report.py"), "--monthly"],
                    capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        try:
            report = json.loads((r.stdout or "").strip().split("\n")[-1])
            api.send_message(chat_id, "❌ Не удалось собрать отчёт")
        except Exception:
            # stdout не JSON — это сам отчёт? нет, --monthly шлёт в TG. Покажем через импорт
            import importlib.util as _iu3
            try:
                spec = _iu3.spec_from_file_location("evrm", str(PROJECT_ROOT / "run_evening_report.py"))
                mod = _iu3.module_from_spec(spec)
                spec.loader.exec_module(mod)
                report = mod.build_monthly()
                api.send_message(chat_id, report[:3900])
            except Exception as e:
                api.send_message(chat_id, f"❌ {e}")
        return True

    # ---- Голосовые ответы ----
    if any(w in t for w in ("включи голосовые ответы", "отвечай голосом", "включи голос")):
        _set_voice_enabled(chat_id, True)
        api.send_message(chat_id, "🎙 Голосовые ответы ВКЛЮЧЕНЫ — бот будет озвучивать ответы.")
        return True
    if any(w in t for w in ("выключи голосовые ответы", "отвечай текстом", "выключи голос")):
        _set_voice_enabled(chat_id, False)
        api.send_message(chat_id, "🔇 Голосовые ответы выключены.")
        return True

    # ---- Напоминания ----
    if re.match(r"^(напомни|напоминание|remind)", t):
        _m()._handle_reminder(api, chat_id, text)
        return True

    # ---- Новая Пошта ----
    np_words = any(w in t for w in ("нова пошт", "нова почт", "новая пошта", "nova poshta",
                                    "novaposhta", "ттн", "посилк", "посылк", "відділенн",
                                    "отделен", "нової пошти", "новой почты"))
    if np_words:
        # авто-ТТН: 14-значное число в тексте = предложить отследить
        m_ttn_auto = re.search(r"\b(\d{14})\b", text)
        if m_ttn_auto and not any(w in t for w in ("отследи", "отследить", "статус", "где")):
            ttn = m_ttn_auto.group(1)
            api.send_message(chat_id,
                             f"📦 Вижу номер посылки <code>{ttn}</code>.\n"
                             f"Напишите «отследи посылку {ttn}» — покажу статус.")
            return True
        # отследить посылку
        m_ttn = re.search(r"(\d{8,14})", text)
        if m_ttn:
            ttn = m_ttn.group(1)
            phone = ""
            m_ph = re.search(r"(\+?380\d{9})", text)
            if m_ph:
                phone = m_ph.group(1)
            api.send_message(chat_id, f"⏳ Отслеживаю посылку {ttn}…")
            data = _run_account_control(["novaposhta", "track", ttn, "--phone", phone])
            if data.get("status") == "ok":
                if not data.get("found"):
                    api.send_message(chat_id, f"📦 <b>{ttn}</b>: посылку не найдено.")
                    return True
                det = data.get("details") or {}
                txt = (f"📦 <b>Новая Пошта · {ttn}</b>\n"
                       f"📍 Статус: <b>{_esc_tg(data.get('tracking_status'))}</b>\n"
                       f"🚚 Маршрут: {_esc_tg(det.get('sender') or '?')} → {_esc_tg(det.get('recipient') or '?')}\n"
                       f"📅 План: {_esc_tg(det.get('scheduled_delivery') or '?')}\n")
                evs = data.get("events") or []
                if evs:
                    txt += "\n🗂 История:\n" + "\n".join(
                        f"• {_esc_tg(e.get('date'))} — {_esc_tg(e.get('event'))}"
                        f"{_esc_tg(' (' + e.get('settlement') + ')') if e.get('settlement') else ''}"
                        for e in evs[-5:])
                api.send_message(chat_id, txt[:3900])
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        # отделения
        if any(w in t for w in ("відділенн", "отделен", "отделение")):
            q = re.sub(r"(найди|найти|покажи|отделен\w*|відділенн\w*|где|де)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            if not q:
                api.send_message(chat_id, "🏢 Напишите «отделение Новой Пошты <город/адрес>»")
                return True
            api.send_message(chat_id, "⏳ Ищу отделения…")
            data = _run_account_control(["novaposhta", "offices", q])
            if data.get("status") == "ok":
                offs = data.get("offices") or []
                if offs:
                    api.send_message(chat_id, "🏢 <b>Отделения:</b>\n" + "\n".join(
                        f"• {_esc_tg(o)}" for o in offs[:8]))
                else:
                    api.send_message(chat_id, f"🏢 Отделения «{q}» не найдены.")
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        # кабинет
        api.send_message(chat_id, "⏳ Открываю кабинет Новой Пошты…")
        data = _run_account_control(["novaposhta", "account"])
        if data.get("status") == "ok":
            txt = (f"📦 <b>Новая Пошта — кабинет</b>\n"
                   f"👤 {_esc_tg(data.get('name') or '?')}\n"
                   f"💰 Баланс: {_esc_tg(data.get('balance') or '—')} грн")
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "📦 Новая Пошта"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Prom.ua ----
    if any(w in t for w in ("пром", "prom.ua", "пром юа")):
        api.send_message(chat_id, "⏳ Захожу в Prom…")
        data = _run_account_control(["prom", "profile"])
        if data.get("status") == "ok":
            txt = (f"🏪 <b>Prom.ua</b>\n"
                   f"🏬 Магазин: {_esc_tg(data.get('shop') or '?')}\n"
                   f"📦 Товаров: {data.get('products') or '?'}\n"
                   f"📋 Заказов: {data.get('orders') or '?'}")
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "🏪 Prom"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Telegram (личный аккаунт, userbot) ----
    if tg_words:
        is_dialog = any(w in t for w in ("чаты", "диалог", "список чатов", "прочитай",
                                         "напиши", "отправь", "боту", "команду боту"))
        if any(w in t for w in ("напиши", "отправь")) and "боту" not in t:
            m = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m.group(1).strip() if m else ""
            target = re.sub(r"^(напиши|отправь)(\s+(в|в\s+телеграм|телеграм|telegram|тг))?\s+", "",
                            text, flags=re.IGNORECASE)
            target = re.sub(r"^(в|телеграм|telegram|тг)\s+", "", target, flags=re.IGNORECASE)
            target = target.split(":", 1)[0].strip(" ,.;:—–")
            if not target or not body:
                api.send_message(chat_id,
                                 "✈️ <b>Telegram</b>: «напиши в телеграм &lt;имя&gt;: &lt;текст&gt;»\n"
                                 "или «напиши боту @username: <команда>»")
                return True
            _pending_confirm[chat_id] = {"kind": "tg_send",
                                         "data": {"ref": target, "text": body}}
            api.send_message(chat_id,
                             f"✈️ Отправить <b>{target}</b> в Telegram:\n«{body[:200]}»\n\n«да» / «нет»")
            return True
        if "боту" in t or (any(w in t for w in ("бот ", "команду боту"))):
            m = re.search(r"@([a-zA-Z0-9_]+)", text)
            bot = m.group(1) if m else None
            command = re.sub(r"^(напиши|отправь|команду)\s+боту\s*@?\w*:?\s*", "", text, flags=re.IGNORECASE).strip()
            if not bot or not command:
                api.send_message(chat_id,
                                 "🤖 <b>Команда боту</b>: «напиши боту @BotFather /start»")
                return True
            _pending_confirm[chat_id] = {"kind": "tg_bot",
                                         "data": {"bot": bot, "command": command}}
            api.send_message(chat_id,
                             f"🤖 Отправить боту <b>@{bot}</b> команду «{command[:150]}»?\n\n«да» / «нет»")
            return True
        # диалоги / чтение
        if any(w in t for w in ("прочитай", "покажи чат", "что в чате")):
            m = re.search(r"(?:телеграм|телеге|тг|чате|чату)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)", text, re.IGNORECASE)
            ref = m.group(1).strip() if m else ""
            api.send_message(chat_id, "⏳ Читаю Telegram…")
            data = _run_account_control(["tg", "read", ref or "Saved Messages", "--limit", "12"])
            if data.get("status") == "ok":
                msgs = data.get("messages") or []
                if not msgs:
                    api.send_message(chat_id, "✈️ В чате нет сообщений.")
                else:
                    api.send_message(chat_id, "✈️ <b>Telegram</b>:\n" + "\n".join(
                        f"{'👤' if not x.get('out') else '🙋'} {_esc_tg(x.get('text', ''))}" for x in msgs[-12:]))
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        api.send_message(chat_id, "⏳ Загружаю чаты Telegram…")
        data = _run_account_control(["tg", "dialogs", "15"])
        if data.get("status") == "ok":
            dialogs = data.get("dialogs") or []
            if dialogs:
                txt = "✈️ <b>Последние чаты Telegram</b>:\n" + "\n".join(
                    f"• {_esc_tg(d.get('name'))}{' 🤖' if d.get('is_bot') else ''}"
                    f"{' 🔴' + str(d.get('unread')) if d.get('unread') else ''}"
                    for d in dialogs[:15])
                api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, "✈️ Чатов нет. Проверьте вход: нужен TG_API_ID/TG_API_HASH.")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- OLX ----
    if any(w in t for w in ("олх", "olx", "объявлен", "объявлени")):
        api.send_message(chat_id, "⏳ Захожу в OLX…")
        data = _run_account_control(["olx", "profile"])
        if data.get("status") == "ok":
            o = data.get("olx", {})
            txt = (f"🛒 <b>OLX</b>\n"
                   f"👤 Имя: {_esc_tg(o.get('name') or '?')}\n"
                   f"📄 Объявлений: {o.get('ads_count') or 0}\n"
                   f"💰 Баланс: {o.get('balance') or 0} грн\n"
                   f"🔑 Логин: {o.get('login')}")
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": o.get("screenshot"),
                                             "caption": "🛒 OLX"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Google Contacts ----
    if any(w in t for w in ("контакт", "телефонная книга", "адресная книга")):
        if any(w in t for w in ("добавь", "создай", "новый контакт", "запиши контакт")):
            m_name = re.search(r"контакт\s+([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,40}?)(?:\s+email\s+([\w.+-]+@[\w-]+\.[\w.]+))?(?:\s+тел[а-я]*\s*([+\d][\d\s().-]{5,})|$)", text, re.IGNORECASE)
            name = m_name.group(1).strip() if m_name else ""
            email = m_name.group(2) if m_name and m_name.group(2) else ""
            phone = m_name.group(3) if m_name and m_name.group(3) else ""
            if not name:
                api.send_message(chat_id,
                                 "👤 <b>Добавление контакта</b>: напишите, например\n"
                                 "«добавь контакт Иван Иванов email ivan@mail.com тел +380501112233»")
                return True
            api.send_message(chat_id, "⏳ Создаю контакт…")
            data = _run_account_control(["google", "contacts_add", "--name", name,
                                         "--email", email, "--phone", phone])
            if data.get("status") == "ok":
                api.send_message(chat_id, f"✅ Контакт <b>{name}</b> создан в Google Контактах.")
            else:
                api.send_message(chat_id, f"⚠️ {data.get('note', data.get('error', '?'))}")
            return True
        if any(w in t for w in ("найди", "поиск", "найди контакт")):
            q = re.sub(r"(найди|поиск|контакт)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            q = re.sub(r"^(в|по)\s+", "", q).strip()
            if not q:
                api.send_message(chat_id, "👤 Напишите «найди контакт &lt;имя&gt;»")
                return True
            api.send_message(chat_id, "⏳ Ищу контакт…")
            data = _run_account_control(["google", "contacts_search", q])
            if data.get("status") == "ok":
                cons = data.get("contacts") or []
                if cons:
                    txt = "👤 <b>Найдено:</b>\n" + "\n".join(
                        f"• {_esc_tg(c.get('name'))} {_esc_tg('(' + c.get('email') + ')') if c.get('email') else ''}"
                        for c in cons[:8])
                    api.send_message(chat_id, txt)
                else:
                    api.send_message(chat_id, f"👤 Контакт «{q}» не найден.")
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        # просто «контакты»
        api.send_message(chat_id, "⏳ Загружаю контакты…")
        data = _run_account_control(["google", "contacts_list", "--limit", "15"])
        if data.get("status") == "ok":
            cons = data.get("contacts") or []
            txt = f"👤 <b>Google Контакты</b> ({data.get('count') or len(cons)}):\n" + "\n".join(
                f"• {_esc_tg(c.get('name'))}" for c in cons[:15])
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "👤 Контакты"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Google ----
    if any(w in t for w in ("кто я", "какой аккаунт", "кто залогинен")):
        _acct_google(api, chat_id, "whoami")
        return True
    if "непрочитан" in t:
        _acct_google(api, chat_id, "unread")
        return True
    if any(w in t for w in ("события", "событий", "расписание", "что в календаре", "что у меня в календаре", "план на день")):
        _acct_google(api, chat_id, "events")
        return True
    if any(w in t for w in ("добавь событие", "добавь в календарь", "создай событие", "запиши в календарь", "новое событие", "создать событие", "добавь встречу", "создай встречу")):
        parsed = _llm_extract_calendar(text)
        title = (parsed.get("title") or "").strip()
        if not title:
            api.send_message(chat_id,
                             "📅 <b>Создание события</b>: напишите, например:\n"
                             "«событие Встреча с Мишей завтра в 14:00»")
            return True
        date = (parsed.get("date") or "").strip()
        time_str = (parsed.get("time") or "").strip()
        desc = (parsed.get("desc") or "").strip()
        data = _run_account_control(["google", "calendar_add", "--title", title,
                                     "--date", date, "--time", time_str, "--desc", desc])
        if data.get("status") == "need_confirm":
            _pending_confirm[chat_id] = {"kind": "calendar_add",
                                         "data": {"title": title, "date": date,
                                                  "time": time_str, "desc": desc}}
            api.send_message(chat_id,
                             f"📅 <b>Подтвердите создание события:</b>\n{title}\n"
                             f"🕐 {data.get('start', date + ' ' + time_str)} → {data.get('end', '')}\n\n"
                             f"«да» — создать, «нет» — отмена")
            shot = data.get("screenshot")
            if shot and os.path.exists(shot):
                try:
                    api.send_photo(chat_id, shot, caption="📅 Предпросмотр")
                except Exception:
                    pass
            return True
        api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
        return True
    if any(w in t for w in ("найди письмо", "найди письма", "поиск в почте", "поиск писем", "поищи", "найди в почте", "найди на почте")):
        q = text
        for w in ("найди письмо", "найди письма", "поиск в почте", "поиск писем",
                  "поищи", "найди в почте", "найди на почте", "найди", "письма"):
            if w.lower() in q.lower():
                q = q.replace(w, "", 1)
        q = q.strip(" :,;—–«»\"'().")
        q = re.sub(r"^(от|по|про|на|в|о|из)\s+", "", q).strip()
        if not q:
            api.send_message(chat_id,
                             "🔍 <b>Поиск в почте</b>: напишите «найди письмо &lt;запрос&gt;»,\n"
                             "например «найди письмо от github»")
            return True
        data = _run_account_control(["google", "gmail_search", q, "5"])
        if data.get("status") == "ok":
            _last_gmail_ids[chat_id] = [e.get("id", "") for e in data.get("emails", [])]
            if data.get("emails"):
                api.send_message(chat_id, _fmt_gmail_list(data))
            else:
                api.send_message(chat_id, f"🔍 По запросу «{q}» писем не найдено.")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("прочитай письмо", "прочитай писмо", "открой письмо",
                            "открой писмо", "покажи письмо", "покажи писмо")):
        m = re.search(r"письм[оае]?\s*№?\s*(\d+)", text, re.IGNORECASE)
        idx = int(m.group(1)) if m else 1
        ids = _last_gmail_ids.get(chat_id) or []
        if not ids:
            # загрузим последние
            data = _run_account_control(["google", "gmail_list", "5"])
            if data.get("status") == "ok":
                ids = [e.get("id", "") for e in data.get("emails", [])]
                _last_gmail_ids[chat_id] = ids
        if not ids or idx < 1 or idx > len(ids):
            api.send_message(chat_id, "❌ Сначала покажите письма («проверь почту»), потом номер.")
            return True
        api.send_message(chat_id, "⏳ Читаю письмо…")
        data = _run_account_control(["google", "gmail_read", ids[idx - 1], "--max", "3000"])
        if data.get("status") == "ok":
            txt = (f"📧 <b>{_esc_tg(data.get('subject'))}</b>\n"
                   f"✉️ {_esc_tg(data.get('from'))}\n"
                   f"🕐 {_esc_tg(data.get('date'))}\n\n"
                   f"{_esc_tg(data.get('body'))[:2500]}")
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("ответь на письмо", "ответь на писмо", "напиши ответ на письмо",
                            "ответить на письмо")):
        m = re.search(r"письм[оае]?\s*№?\s*(\d+)", text, re.IGNORECASE)
        idx = int(m.group(1)) if m else 1
        ids = _last_gmail_ids.get(chat_id) or []
        body = ""
        m_colon = re.search(r":\s*(.+)$", text, re.IGNORECASE)
        if m_colon:
            body = m_colon.group(1).strip()
        if not ids or idx < 1 or idx > len(ids):
            api.send_message(chat_id, "❌ Сначала покажите письма, потом номер.")
            return True
        if not body:
            api.send_message(chat_id, "❌ Напишите текст ответа после двоеточия:\n"
                                      "«ответь на письмо 1: привет, получил, спасибо»")
            return True
        _pending_confirm[chat_id] = {"kind": "gmail_reply",
                                     "data": {"msg_id": ids[idx - 1], "idx": idx, "text": body}}
        api.send_message(chat_id,
                         f"📧 Ответ на письмо №{idx}:\n«{body[:200]}»\n\nОтправить? «да» / «нет»")
        return True
    if any(w in t for w in ("неделю", "план на неделю", "события на неделю",
                            "что на неделе", "на неделе")):
        api.send_message(chat_id, "⏳ Смотрю неделю в календаре…")
        data = _run_account_control(["google", "calendar_week"])
        if data.get("status") == "ok":
            evs = data.get("events") or []
            if evs:
                txt = "📅 <b>События на неделю:</b>\n" + "\n".join(f"• {_esc_tg(x)}" for x in evs)
            else:
                txt = "📅 На этой неделе событий нет."
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "📅 Неделя"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("файлы на диске", "что на диске", "список диска",
                            "файлы в гугл диске", "файлы на гугл диске", "диск список",
                            "что в гугл диске", "что в google drive")):
        api.send_message(chat_id, "⏳ Загружаю Google Диск…")
        data = _run_account_control(["google", "drive_list", "--limit", "15"])
        if data.get("status") == "ok":
            files = data.get("files") or []
            if files:
                txt = "🗂 <b>Google Диск</b>:\n" + "\n".join(f"• {_esc_tg(f.get('title'))}" for f in files)
            else:
                txt = "🗂 На диске пусто."
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "🗂 Диск"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("скачай файл", "скачай с диска", "загрузи файл с диска",
                            "скинь файл", "скачай")):
        ref = text
        for w in ("скачай файл", "скачай с диска", "загрузи файл с диска", "скинь файл",
                  "скачай", "файл"):
            if w.lower() in ref.lower():
                ref = ref.replace(w, "", 1)
        ref = ref.strip(" :,;—–«»\"'().")
        if not ref:
            api.send_message(chat_id, "🗂 Скажите, какой файл скачать:\n«скачай файл <имя или id>»")
            return True
        api.send_message(chat_id, "⏳ Скачиваю с Диска…")
        data = _run_account_control(["google", "drive_download", ref])
        if data.get("status") == "ok":
            path = data.get("path")
            name = data.get("name") or "файл"
            if path and os.path.exists(path):
                try:
                    api.send_document(chat_id, path, caption=f"🗂 {name}")
                except Exception as e:
                    api.send_message(chat_id, f"✅ Скачал, но не смог отправить файл: {e}")
            else:
                api.send_message(chat_id, f"✅ Скачал ({data.get('size', '?')} байт), файл: {path}")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("создай документ", "новый документ", "сделай документ", "гугл документ", "документ в гугле", "создай гугл док")):
        parsed = _llm_extract_gmail(text)
        title = (parsed.get("subject") or "").strip()
        content = (parsed.get("body") or "").strip()
        if not title:
            m = re.search(r"документ\s+([\w\s-]{2,60}?)(?:[,.;]|$)", text, re.IGNORECASE)
            if m:
                title = m.group(1).strip()
        api.send_message(chat_id, "⏳ Создаю документ…")
        data = _run_account_control(["google", "docs_create", "--title", title, "--content", content])
        if data.get("status") == "ok":
            api.send_message(chat_id, f"📄 <b>Документ создан</b>:\n🔗 {data.get('url')}")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("календар", "calendar")):
        _acct_google(api, chat_id, "calendar")
        return True
    if any(w in t for w in ("диск", "drive", "файл")):
        _acct_google(api, chat_id, "drive")
        return True
    if any(w in t for w in ("отправ", "напиши письмо", "создай письмо")):
        # извлечь параметры через LLM
        parsed = _llm_extract_gmail(text)
        to = (parsed.get("to") or "").strip()
        if not to:
            api.send_message(chat_id, "❌ Не нашёл адрес получателя. Напишите, например: "
                                      "«отправь письмо ivan@gmail.com, тема Встреча, текст: привет»")
            return True
        subject = (parsed.get("subject") or "").strip() or "(без темы)"
        body = (parsed.get("body") or "").strip()
        _pending_confirm[chat_id] = {"kind": "gmail",
                                     "data": {"to": to, "subject": subject, "body": body}}
        api.send_message(chat_id,
                         f"📧 Готово к отправке:\n📮 Кому: {to}\n📝 Тема: {subject}\n"
                         f"💬 Текст: {body[:200]}\n\n"
                         f"Отправить? Напишите «да» — или «нет» для отмены.")
        return True
    if any(w in t for w in ("почт", "gmail", "email", "письм")):
        _acct_google(api, chat_id, "list")
        return True
    # по умолчанию — показать меню аккаунтов
    api.send_message(chat_id,
                     "🌐 Управление аккаунтами:\n"
                     "• Google: «проверь почту», «непрочитанные», «кто я», «календарь», «диск», «отправь письмо …»\n"
                     "• Instagram: «мой инстаграм», «мои посты», «скрин профиля»",
                     reply_markup=_m().ACCOUNTS_MENU_KEYBOARD)
    return True


def cmd_accounts() -> str:
    return ("🌐 <b>Управление аккаунтами</b>\n\n"
            "Можно просто написать обычным текстом, например:\n"
            "• «проверь мою почту» / «сколько непрочитанных» / «найди письмо …»\n"
            "• «кто я в гугле» · «события на сегодня» · «добавь событие …»\n"
            "• «создай документ …» · «покажи календарь» · «отправь письмо …»\n"
            "• «мой инстаграм» · «директ» · «лайкни &lt;ссылка&gt;»\n"
            "• «покажи фейсбук» · «тикток» · «олх» / «мои объявления»\n"
            "• «подпишись на @…» / «отпишись от @…»\n\n"
            "Или выберите раздел:")


def cmd_google(args: str) -> str:
    a = args.strip().lower()
    if not a:
        return ("🌐 <b>Google</b>\n\nКоманды:\n"
                "/google whoami · /google unread · /google list\n"
                "/google search &lt;запрос&gt; · /google calendar · /google drive\n"
                "/google events · /google mailshot · /google send\n"
                "Или просто напишите «проверь почту», «события на сегодня», «создай документ …»")
    return "🌐 Google: укажите подкоманду."


def cmd_instagram(args: str) -> str:
    a = args.strip().lower()
    if not a:
        return ("📸 <b>Instagram</b>\n\nКоманды:\n"
                "/instagram profile · /instagram posts · /instagram screenshot\n"
                "Или просто напишите «мой инстаграм», «лайкни &lt;ссылка&gt;», «подпишись на @…»")
    return "📸 Instagram: укажите подкоманду."
